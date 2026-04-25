# Sprint 31.9 SPRINT-CLOSE: Campaign Seal + 3 Post-31.9 DISCOVERY Stubs

> Drafted Phase 2. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign. **Ceremonial close** — book-closing on Sprint 31.9 + setup for post-31.9 sprint succession.

## Scope

**Finding addressed:**
Sprint 31.9 is a multi-day campaign with ~80+ FIX-NN/IMPROMPTU-NN sessions,
~45 closed DEFs, ~20 new DEFs opened and dispositioned, ~25 P-lessons, and
3 post-31.9 sprints now queued. This session closes the sprint book and
opens the next 3 sprint directories with discovery-grade stubs.

**Files produced/modified:**
- `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` (NEW — the top-level sprint summary)
- `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` — SEAL banner + final state
- `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — final CLEAR marks on all stages
- `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` — archive (mark superseded by SPRINT-31.9-SUMMARY)
- `docs/sprints/post-31.9-component-ownership/DISCOVERY.md` (NEW)
- `docs/sprints/post-31.9-reconnect-recovery/DISCOVERY.md` (NEW)
- `docs/sprints/post-31.9-alpaca-retirement/DISCOVERY.md` (NEW)
- `CLAUDE.md` — update "Active sprint" and "Next sprint" pointers; sprint-history reference bumped
- `docs/sprint-history.md` — new row for Sprint 31.9 with final numbers
- `docs/project-knowledge.md` — active sprint pointer updated

**Safety tag:** `safe-during-trading` — documentation only. Paper trading continues.

**Theme:** Ceremonial close. Prove all stages CLEAR via the tracker. Produce a canonical summary that future operators / audits can read as the single entry point. Seed the 3 successor sprints with enough discovery material to start their planning conversations.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
# Paper trading continues.
```

### 2. Campaign readiness check

Before running SPRINT-CLOSE, all these sessions MUST be CLEAR:

```bash
# Verify IMPROMPTU-04 through IMPROMPTU-09 + RETRO-FOLD all landed:
ls docs/sprints/sprint-31.9/IMPROMPTU-*-closeout.md
ls docs/sprints/sprint-31.9/IMPROMPTU-*-review.md
ls docs/sprints/sprint-31.9/RETRO-FOLD-closeout.md
ls docs/sprints/sprint-31.9/RETRO-FOLD-review.md
```

**Required closeouts:**
- IMPROMPTU-04 (DEF-199 A1 fix) ✓ needed
- IMPROMPTU-CI (DEF-200 observatory WS) ✓ needed
- IMPROMPTU-05 (deps & infra) ✓ needed
- IMPROMPTU-06 (test-debt) ✓ needed
- IMPROMPTU-07 (doc-hygiene + UI) ✓ needed
- IMPROMPTU-08 (architecture.md API catalog) ✓ needed
- IMPROMPTU-09 (verification sweep) ✓ needed
- RETRO-FOLD (P1–P25 metarepo fold-in) ✓ needed

Each must have a CLEAR verdict in its review file. If any is CONCERNS or
ESCALATE, SPRINT-CLOSE does not run until resolution.

```bash
# Quick CLEAR verdict scan:
grep -l "verdict.*CLEAR\|Verdict:.*CLEAR" docs/sprints/sprint-31.9/*-review.md
# Expected: 8 matches (one per session above)
```

### 3. CI readiness

The most recent commit on `origin/main` must have a green CI run.

```bash
git log --oneline origin/main -1
# Record: SHA and CI URL
```

If CI is red, SPRINT-CLOSE does not run until CI is green. Find the red root cause and address it first.

### 4. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count: __________ (final campaign baseline)
cd argus/ui && npx vitest run --reporter=dot 2>&1 | tail -5 && cd -
# Record Vitest count: __________
```

### 5. Branch & workspace

```bash
git checkout main
git pull --ff-only
git status  # Expected: clean
```

## Pre-Flight Context Reading

1. Read these files (in order):
   - `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` — the master plan. Use as the skeleton for SPRINT-31.9-SUMMARY.
   - `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` — final DEF register + session history
   - `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — stage-by-stage completeness matrix + P1–P25 lessons
   - All 8 session close-outs (IMPROMPTU-04 / CI / 05 / 06 / 07 / 08 / 09 + RETRO-FOLD)
   - Earlier campaign close-outs: FIX-00 through FIX-19 (whatever was run before Sprint 31.9 renamed into campaign-close phase) — the tracker will tell you what's in scope
   - `CLAUDE.md` — current "Active sprint" + "Next sprint" pointers
   - `docs/sprint-history.md` — existing sprint history format

2. Collect the final campaign statistics:
   - Total test delta (pytest + Vitest) from baseline to final
   - Total commits on `main` during the campaign
   - Total DEFs opened
   - Total DEFs closed
   - Total new DECs (should be 0 if campaign stayed inside established patterns)
   - Total sessions run (FIX-NN + IMPROMPTU-NN + RETRO-FOLD)
   - Total workflow metarepo commits (from RETRO-FOLD)

3. For the 3 post-31.9 sprints, collect their deferred-items scope from:
   - `CLAUDE.md` DEF register (items flagged for specific post-31.9 sprints)
   - `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` §"Category 2 — NAMED-HORIZON DEFERRED"

## Objective

Produce the canonical artifacts that mark Sprint 31.9 as closed and seed
the 3 successor sprints for planning. This session does NOT plan those
successor sprints — it just ensures each has a DISCOVERY.md with enough
context that a future planning conversation can hit the ground running.

## Requirements

### Requirement 1: SPRINT-31.9-SUMMARY.md

Create `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` with this structure:

```markdown
# Sprint 31.9: Health & Hardening — Campaign Summary

**Campaign:** Sprint 31.9 Health & Hardening (derived from audit-2026-04-21 + Apr 22 paper session debrief)
**Dates:** {start} – {end}
**Final HEAD:** `{SHA}` on `origin/main`
**Final test state:** {pytest} pytest / {vitest} Vitest / CI green ({CI URL})
**Sessions run:** {N} total ({FIX-NN count} audit-remediation sessions + {IMPROMPTU-NN count} impromptu sessions + RETRO-FOLD)

## What Sprint 31.9 Achieved

{1-paragraph prose summary — audit remediation, paper-session debrief responses, test/infra hygiene, campaign protocol evolution}

## DEF Register Delta

| Metric | Count |
|---|---|
| DEFs opened during campaign | {N} |
| DEFs closed during campaign | {M} |
| DEFs deferred to named-horizon sprints | {K} |
| DEFs remaining MONITOR | {P} |

Full list: see RUNNING-REGISTER.md.

## DEC Delta

{N} new DECs landed / {M} DECs superseded / {K} DECs amended. Full list: docs/decision-log.md entries DEC-{start}–DEC-{end}.

## Campaign Lessons (P1–P25)

Summary of each lesson + where it landed in the `claude-workflow` metarepo.
See `RETRO-FOLD-closeout.md` for full details.

| P # | 1-line lesson | Metarepo destination |
|---|---|---|
| P1 | ... | ... |
| ... | ... | ... |
| P25 | ... | ... |

## Session Index

Brief table of every session run in the campaign:

| Session | Date | Verdict | Key DEFs closed | Commits |
|---|---|---|---|---|
| FIX-00 | ... | CLEAR | ... | ... |
| ... | ... | ... | ... | ... |
| RETRO-FOLD | ... | CLEAR | ... | ... |

## Handoff to Post-31.9 Sprints

Three successor sprints are queued with DISCOVERY stubs:

1. **post-31.9-component-ownership** — DEFs {list}; see `docs/sprints/post-31.9-component-ownership/DISCOVERY.md`
2. **post-31.9-reconnect-recovery** — DEFs {list}; see `docs/sprints/post-31.9-reconnect-recovery/DISCOVERY.md`
3. **post-31.9-alpaca-retirement** — DEFs {list}; see `docs/sprints/post-31.9-alpaca-retirement/DISCOVERY.md`

Next sprint in the build-track queue (per DEC-379 decomposition): {Sprint 31B or whichever post-31.9 sprint is scheduled first per roadmap.md}.

## Closing Statement

Sprint 31.9 closed on {date}. {1-sentence closing note — e.g., "Campaign delivered X, Y, Z; paper trading cleared to continue with the hardened posture; post-31.9 succession clearly scoped."}

---

**Maintainer note:** This document is the canonical sprint summary. The campaign-close plan (`CAMPAIGN-CLOSE-PLAN.md`) and running register are preserved in the same directory as historical artifacts but should not be updated further.
```

### Requirement 2: Seal RUNNING-REGISTER.md

Update the top banner of `RUNNING-REGISTER.md`:

```markdown
<!-- ⛔ SEALED: Sprint 31.9 closed on {date}. This document is now read-only history.
     Canonical summary: SPRINT-31.9-SUMMARY.md
     Do not update further. Next sprint's running register lives in its own directory. -->
```

Move every remaining "open" row to final disposition. No row should be TODO or WIP by close.

### Requirement 3: Seal CAMPAIGN-COMPLETENESS-TRACKER.md

Update the top banner similarly:

```markdown
<!-- ⛔ SEALED: Sprint 31.9 closed on {date}. All stages CLEAR. Canonical summary: SPRINT-31.9-SUMMARY.md -->
```

Confirm every stage row shows CLEAR or explicit-deferral-with-reason. No AMBER or unresolved rows.

### Requirement 4: Archive CAMPAIGN-CLOSE-PLAN.md

Add a banner:

```markdown
<!-- 📦 ARCHIVED: This plan document was the working master during Sprint 31.9 campaign-close (Phase 1a – SPRINT-CLOSE). It has been superseded by SPRINT-31.9-SUMMARY.md. Preserved here for reference. -->
```

No content changes beyond the banner.

### Requirement 5: Create 3 DISCOVERY.md stubs

For each of the 3 post-31.9 sprints, create a DISCOVERY.md with this structure.
**These are stubs, not plans. The actual sprint planning is a separate future
conversation. DISCOVERY.md's role is to ensure the planning conversation has
accurate context.**

```markdown
# Sprint `{sprint-id}` Discovery Notes

> Discovery-grade seed doc. Written at Sprint 31.9 SPRINT-CLOSE. Enough context to start a planning conversation without re-reading the full Sprint 31.9 history. **Not a plan; not a spec.** Planning conversation produces the actual sprint package.

## Sprint Identity

- **Sprint ID:** `{sprint-id}` (e.g., `post-31.9-component-ownership`)
- **Predecessor:** Sprint 31.9 (Health & Hardening)
- **Build-track position:** {per-roadmap-position, if known}
- **Discovery date:** {date}

## Theme

{1–2 paragraph description of what this sprint is intended to accomplish. Pull from the DEF cluster it addresses.}

## Deferred-Items Scope

DEFs explicitly queued for this sprint:

| DEF # | Title | Source | Notes |
|---|---|---|---|
| DEF-{N} | ... | Sprint 31.9 debrief | ... |
| ... | ... | ... | ... |

Total: {N} DEFs in scope. See CLAUDE.md for full descriptions.

## Known Dependencies / Constraints

- {e.g., "Requires component-ownership refactor to complete before Alpaca retirement can proceed"}
- {e.g., "Blocked on Sprint 31B Research Console landing — shared file: argus/api/routes/experiments.py"}
- {e.g., "Blocked on live-paper-trading deployment — needs production data patterns"}

## Open Questions (for planning conversation)

- {e.g., "Should component-ownership be a single sprint or decomposed into component-ownership-A + B?"}
- {e.g., "Is there an adversarial-review-required subset here, or is standard Tier 2 sufficient across the board?"}
- {e.g., "Timing-wise: before or after paper-to-live transition?"}

## Context Pointers

- Sprint 31.9 summary: `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`
- Apr 22 debrief: `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` {if this sprint's DEFs originated from that debrief}
- Related DECs: `docs/decision-log.md` DEC-{N}, DEC-{M}
- Build-track queue: `docs/roadmap.md`

## Not-in-Scope

Explicitly exclude:
- {things tempting to bundle but that belong elsewhere}

## Pre-Planning Checklist

Before running the planning conversation:
- [ ] All DEFs in scope still OPEN (verify CLAUDE.md)
- [ ] No dependencies blocked
- [ ] Build-track queue supports starting this sprint next
- [ ] Relevant Sprint 31.9 outcomes confirmed (e.g., "IMPROMPTU-07 variant-count note landed, so we can rely on 22 shadow variants in scope")
```

**Create three of these:**

1. `docs/sprints/post-31.9-component-ownership/DISCOVERY.md` — DEFs 175, 182, 193, 197, 014, C7. Theme: unify Strategy + Broker + DataService ownership boundaries that accreted across sprints.
2. `docs/sprints/post-31.9-reconnect-recovery/DISCOVERY.md` — DEFs 177, 184, 194, 195, 196, F-04. Theme: robust recovery posture after IBKR/Databento session-reset events, informed by Apr 22 cascade post-mortem.
3. `docs/sprints/post-31.9-alpaca-retirement/DISCOVERY.md` — DEFs 178, 183. Theme: fully retire AlpacaBroker incubator path; move to dedicated package or remove.

Populate each with actual DEF numbers and theme descriptions — don't leave placeholder text.

### Requirement 6: Update CLAUDE.md pointers

1. `CLAUDE.md` "Active sprint" → update to next build-track sprint (per roadmap.md)
2. "Sprint history" reference → bump sprint count / cross-ref new sprint-history.md row
3. Add SPRINT-31.9-SUMMARY.md to the Reference Documents table

### Requirement 7: Update sprint-history.md

Add a final row for Sprint 31.9 with the final numbers:

```markdown
| 31.9 | Health & Hardening (Campaign — audit-2026-04-21 Phase 3 + Apr 22 paper debrief + infra hygiene) | {final pytest}+{final vitest}V | {date range} | DEC-{range} + P1–P25 retro-folded to metarepo |
```

Follow the existing table format exactly.

### Requirement 8: Update project-knowledge.md

Update the "Active sprint" pointer and adjust the "Next" annotation so the doc matches CLAUDE.md.

## Constraints

- **Do NOT modify** any argus runtime code. Doc-only session.
- **Do NOT change** the 8 session close-out/review files already landed. They are historical records.
- **Do NOT retroactively** fix wording issues in older sprint close-outs. If something's wrong, note it in SPRINT-31.9-SUMMARY without editing the source doc.
- **Do NOT plan** the 3 successor sprints. DISCOVERY.md is a seed, not a plan. The actual planning is a future conversation.
- **Do NOT open new DEFs** unless the close-out verification for this session surfaces something (rare at this stage).
- **Do NOT modify** the `workflow/` submodule. RETRO-FOLD already did that work.
- Work directly on `main`.

## Test Targets

- pytest full suite unchanged (no code changes)
- No new tests
- CI remains green (sanity — this is doc work)

## Definition of Done

- [ ] `SPRINT-31.9-SUMMARY.md` created with all 8 sections populated
- [ ] `RUNNING-REGISTER.md` sealed with banner
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` sealed with banner; all stages CLEAR
- [ ] `CAMPAIGN-CLOSE-PLAN.md` archived with banner
- [ ] 3 DISCOVERY.md stubs created with populated DEF scope + theme + open questions
- [ ] CLAUDE.md pointers updated (Active sprint, Sprint history reference, Reference Documents)
- [ ] `docs/sprint-history.md` — Sprint 31.9 row added
- [ ] `docs/project-knowledge.md` — Active sprint pointer updated
- [ ] Close-out at `docs/sprints/sprint-31.9/SPRINT-CLOSE-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/SPRINT-CLOSE-review.md`
- [ ] Final green CI URL cited

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| SPRINT-31.9-SUMMARY.md has all 8 sections | TOC check |
| RUNNING-REGISTER.md has SEAL banner at top | Read first line |
| CAMPAIGN-COMPLETENESS-TRACKER.md has all stages CLEAR | Grep for non-CLEAR |
| 3 DISCOVERY.md files exist | `ls docs/sprints/post-31.9-*/DISCOVERY.md` |
| Each DISCOVERY.md has populated DEF scope (not placeholders) | Per-file read |
| CLAUDE.md Active sprint is NOT "31.9" anymore | Grep |
| sprint-history.md has Sprint 31.9 row | Grep |
| No argus/ or tests/ or config/ modified | `git diff argus/ tests/ config/` empty |

## Close-Out

Write close-out to: `docs/sprints/sprint-31.9/SPRINT-CLOSE-closeout.md`

Include:
1. **Final campaign statistics** (test delta, commits, DEFs, DECs, sessions)
2. **SPRINT-31.9-SUMMARY.md commit SHA**
3. **3 DISCOVERY.md commit SHAs**
4. **Banner/SEAL commit SHA** (if separate from summary commit)
5. **CLAUDE.md + sprint-history.md + project-knowledge.md commit SHA**
6. **Final green CI URL**
7. **Closing statement** — one-paragraph reflection on the campaign

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

Invoke @reviewer after close-out.

Provide:
1. Review context: all campaign artifacts + CAMPAIGN-CLOSE-PLAN.md + RUNNING-REGISTER.md
2. Close-out path: `docs/sprints/sprint-31.9/SPRINT-CLOSE-closeout.md`
3. Diff range: `git diff HEAD~N`
4. Files that should NOT have been modified:
   - Any argus/ code file
   - Any config/ file
   - Any tests/ file
   - Any pre-existing session close-out or review file
   - Any workflow/ submodule file
   - Any audit-2026-04-21 doc back-annotation

The @reviewer writes to `docs/sprints/sprint-31.9/SPRINT-CLOSE-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Verify SUMMARY completeness.** All 8 sections present + populated. Statistics check out against actual campaign artifacts.
2. **Verify SEAL banners.** RUNNING-REGISTER.md and CAMPAIGN-COMPLETENESS-TRACKER.md both have visible banners at top that mark them read-only.
3. **Verify 3 DISCOVERY.md stubs.** Each has the standard structure + populated DEF scope + at least 2 open questions.
4. **Verify CLAUDE.md no longer says 31.9 is active.** "Active sprint" pointer advanced.
5. **Verify no retroactive edits to historical files.** Pre-existing close-outs / reviews / decision-log entries should be untouched.
6. **Verify full pytest suite still passes.**
7. **Verify green CI URL is for the SPRINT-CLOSE commit.**

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta = 0
- Vitest count unchanged
- No scope boundary violation
- CLAUDE.md "Active sprint" pointer advanced past 31.9

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- SPRINT-31.9-SUMMARY.md missing sections or using placeholder text
- SEAL banners missing from register/tracker
- Any DISCOVERY.md is placeholder-only (no real DEF scope populated)
- Any argus/ or tests/ or config/ file modified
- Any historical close-out/review/decision-log edited
- CLAUDE.md still says Sprint 31.9 is active
- Full pytest broken

## Post-Review Fix Documentation

Standard protocol.

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **Campaign ledger:** final pytest, vitest, commits, DEFs, sessions
4. **SPRINT-31.9-SUMMARY.md path** — operator reads this; it's the canonical artifact
5. **3 DISCOVERY.md paths** — ready for future planning conversations
6. **Updated CLAUDE.md** — operator confirms Active sprint pointer is correct
7. Final green CI URL
8. One-line summary: `Sprint 31.9 SEALED. SPRINT-31.9-SUMMARY.md is canonical. 3 post-31.9 DISCOVERY stubs created. Build-track advances to {next-sprint-id}. CI: {URL}. Campaign closed.`
