# Sprint synthesis-2026-04-26: Work Journal Handoff

> **This document is the operator-facing coordination prompt.** It tells you (Steven) how to execute the sprint across the 6 sessions in human-in-the-loop mode. Paste this into your Work Journal conversation (or print it and check off items as you go). The Work Journal conversation is the campaign coordination surface for this sprint.
>
> **Sprint structure:** Session 0 (argus-side) → Sessions 1–6 (metarepo-side, serial). Total operator-attended time: ~7.5 hours, splittable across multiple days. Each session is a fresh Claude Code conversation; do NOT reuse a single conversation across sessions.

---

## Sprint Overview

### Goal

Fold the 3 unsynthesized post-RETRO-FOLD evolution notes (2026-04-21) + 4 floating retrospective candidates (P26–P29) + 5 process patterns (P30–P34) into the `claude-workflow` metarepo so they auto-fire on subsequent campaigns. Land the keystone Pre-Flight wiring that retroactively activates RETRO-FOLD's P1–P25 RULE coverage.

### Sessions

| # | Name | Files Modified | Files Created | Est. Time |
|---|---|---|---|---|
| 0 | Argus-side input set | `SPRINT-31.9-SUMMARY.md` (+optional `argus/CLAUDE.md`) | — | ~15 min |
| 1 | Keystone wiring + RULEs + close-out | universal.md, close-out.md, implementation-prompt.md, review-prompt.md | — | ~75 min |
| 2 | Housekeeping templates + scaffold + evolution-notes | work-journal-closeout.md, doc-sync-automation-prompt.md, scaffold/CLAUDE.md, evolution-notes/README.md, 3 evolution notes | — | ~60 min |
| 3 | campaign-orchestration + impromptu-triage | impromptu-triage.md, bootstrap-index.md | campaign-orchestration.md | ~90 min |
| 4 | operational-debrief | bootstrap-index.md | operational-debrief.md | ~60 min |
| 5 | Templates + validator | bootstrap-index.md | stage-flow.md, scoping-session-prompt.md, phase-2-validate.py | ~75 min |
| 6 | Audit expansion + sprint-planning | codebase-health-audit.md (1.0.0 → **2.0.0**), sprint-planning.md | — | ~90 min |
| Post | Post-sprint doc-sync | README.md (count drift) + verification | — | ~25 min |

### Dependency chain

Strict serial: 0 → 1 → 2 → 3 → 4 → 5 → 6 → Post-sprint doc-sync.

### Sprint package files (all in `argus/docs/sprints/synthesis-2026-04-26/`)

- `design-summary.md` — Phase B compaction insurance
- `sprint-spec.md` — full deliverable list with acceptance criteria
- `spec-by-contradiction.md` — explicit OUT-of-scope items + edge cases
- `session-breakdown.md` — per-session scope + compaction-risk scoring
- `escalation-criteria.md` — when to halt and route to operator
- `regression-checklist.md` — 20 cross-session invariants
- `doc-update-checklist.md` — within-sprint + post-sprint doc-sync work
- `review-context.md` — single shared review context for @reviewer subagent
- `synthesis-2026-04-26-session-N-impl.md` — implementation prompt per session (N = 0..6)
- `post-sprint-doc-sync-prompt.md` — final doc-sync after Session 6
- This file — operator-facing coordination prompt

---

## Per-Session Execution Flow

For each of Sessions 0–6, follow this loop:

### Step 1: Verify prior-session prerequisites

The session's implementation prompt has a Pre-Flight section that checks prior-session outputs are in place. Run those checks BEFORE pasting the prompt into Claude Code — if they fail, the prior session didn't complete and you'll save time catching it now.

For Session 0: no prerequisite checks needed (foundational).
For Sessions 1+: the Pre-Flight verifies prior session(s) landed via grep/ls commands.

### Step 2: Open a fresh Claude Code conversation

Start a new Claude Code session. Do NOT reuse a previous session's conversation — fresh context per session is intentional, both for compaction risk and for keystone Pre-Flight wiring (which expects each session to read `.claude/rules/universal.md` at start).

### Step 3: Paste the implementation prompt

Open `argus/docs/sprints/synthesis-2026-04-26/synthesis-2026-04-26-session-N-impl.md` for the session you're executing. Copy the entire content. Paste into Claude Code.

### Step 4: Let Claude Code execute

Claude Code will:
1. Run Pre-Flight checks (and HALT if any fail).
2. Read context files.
3. Execute the session's sub-phases.
4. Write the close-out report to `argus/docs/sprints/synthesis-2026-04-26/session-N-closeout.md`.
5. Commit (cross-repo: metarepo commit + argus submodule pointer advance).
6. Push.
7. Wait for green CI.
8. Invoke @reviewer subagent for Tier 2 review.
9. @reviewer writes review report to `argus/docs/sprints/synthesis-2026-04-26/session-N-review.md`.

You'll see the session's progress in real-time. Most sessions complete in their listed time-budget; large sessions (3, 6) may run slightly longer.

### Step 5: Read the close-out + review

After Claude Code completes:

1. Open `session-N-closeout.md`. Verify:
   - Sub-phases all completed
   - Verification grep outputs match expected
   - No FLAGGED items in self-assessment
   - The structured-closeout JSON appendix at the end has `"verdict": "CLEAN"` or `"verdict": "MINOR_DEVIATIONS"`
2. Open `session-N-review.md`. Verify the @reviewer's structured-verdict JSON has `"verdict": "CLEAR"` or `"verdict": "CONCERNS_RESOLVED"`.

### Step 6: Handle the verdict

| Verdict | Action |
|---|---|
| CLEAR | Proceed to next session |
| CONCERNS_RESOLVED | Proceed to next session (the implementer fixed in-session) |
| CONCERNS (unresolved) | Read the @reviewer's findings; decide whether to fix-in-session by re-prompting Claude Code, or accept and proceed |
| ESCALATE | **STOP.** See "Escalation Handling" below. Do NOT proceed to next session until resolved. |

### Step 7: Update this Work Journal conversation with session status

Paste a brief status note here:

```
Session N completed YYYY-MM-DD HH:MM
- Verdict: CLEAR | CONCERNS_RESOLVED | CONCERNS | ESCALATE
- Close-out: argus/docs/sprints/synthesis-2026-04-26/session-N-closeout.md
- Review: argus/docs/sprints/synthesis-2026-04-26/session-N-review.md
- Notes: [any judgment calls, deviations, or operator notes]
- Proceeding to: Session N+1 | (paused for escalation)
```

This is the campaign coordination surface's running register. After Session 6, the running register accumulates into the sprint-close summary.

---

## Escalation Handling

When @reviewer reports ESCALATE (verdict in the JSON appendix), the failure mode is structural and requires operator review.

### Read the escalation triggers

The @reviewer's review report names which escalation criteria fired (A1 through D3 — see `escalation-criteria.md`). Common triggers and operator actions:

| Trigger | Description | Action |
|---|---|---|
| A1 | ARGUS runtime modified (paths under argus/argus, argus/tests, etc.) | Revert the runtime change; resume |
| A2 | Evolution-note body modified | Revert body changes; preserve only metadata header; resume |
| A3 | RETRO-FOLD content semantic regression (RULE-001–050 bodies altered) | Critical — review the diff; revert; consider Tier 3 architectural review |
| B1 | Keystone Pre-Flight wiring missing or advisory | Sprint failure — Session 1 must redo with imperative wording |
| B2 | Bootstrap routing miss for new protocol | Add routing entry as follow-on commit; resume |
| B3 | Safety-tag taxonomy reintroduced as recommended pattern | Remove the reintroduction; verify §2.9 anti-pattern addendum is correctly framed |
| B4 | F1–F10 finding not addressed | Map missed findings + fix in follow-on commit (Session 6 close-out has the explicit table) |
| C1 | Workflow-version regression | Bump correctly in follow-on commit |
| C2 | phase-2-validate.py invocation phrased advisorially | Rewrite as imperative gate language |
| C3 | Compaction-driven regression | Discard session commits; restart in fresh Claude Code conversation |
| C4 | Forward-dep unresolved by Session 5 | Verify scoping-session-prompt.md exists; create if Session 5 dropped it |
| D1 | Session N started without Session N-1 landing | Halt; complete prior session first |
| D2 | Tier 2 review can't verify gates | Manually verify; produce corrected close-out |
| D3 | Scope creep beyond OUT items | Revert out-of-scope changes |

### Tier 3 review

For escalations triggered by A3, repeated B-category failures, or if the failure suggests sprint design is flawed (not just execution error), invoke a Tier 3 architectural review. See `protocols/tier-3-review.md`. Tier 3 examines whether the failure indicates a flaw in the sprint design itself (e.g., the keystone wiring concept was wrong) versus a pure execution error (e.g., the implementer dropped the keystone step).

For most escalations, operator review without Tier 3 is sufficient — the escalation criteria + sprint spec + spec-by-contradiction are enough to make the corrective decision.

### Logging escalations

Each escalation gets a brief note in this Work Journal conversation under the relevant session's status:

```
ESCALATION (Session N, trigger XN): [description]
- Decision: revert | fix-in-place | extend-scope | redo-session
- Resolved YYYY-MM-DD HH:MM
- Follow-on commit: [SHA]
```

If the escalation has cross-sprint implications (e.g., reveals a structural issue in another protocol), log it as a follow-on DEC entry in the sprint close-out's "judgment calls" section.

---

## @reviewer Subagent Failure Fallback

If the @reviewer subagent invocation fails (Claude Code reports it can't invoke the subagent, or the subagent returns an error), fall back to a manual review:

1. **Open a fresh Claude Code session** (not the implementation session — needs read-only, separate context).
2. **Paste this prompt:**
   ```
   You are conducting a Tier 2 review for sprint synthesis-2026-04-26 Session N.

   Read these files:
   1. .claude/skills/review.md (the review skill — follow its protocol)
   2. argus/docs/sprints/synthesis-2026-04-26/review-context.md (the sprint contract)
   3. argus/docs/sprints/synthesis-2026-04-26/session-N-closeout.md (the implementer's report)
   4. The session's diff: cd argus/workflow && git diff HEAD~1 (and cd argus && git diff HEAD~1)

   Produce a Tier 2 review report with structured-verdict JSON appendix per the review skill. Write the report to argus/docs/sprints/synthesis-2026-04-26/session-N-review.md.

   This is a READ-ONLY review session. Do NOT modify any source code, configuration, or documentation other than the review report itself.
   ```
3. Replace `N` with the session number.
4. The fallback review produces the same structured verdict; treat it as if the @reviewer subagent had run.

Reasons subagent invocation might fail include: Claude Code update changing the subagent invocation API; model unavailability for the subagent; configuration drift in `.claude/agents/`. The fallback handles all cases without sprint disruption.

---

## Sprint-End Wrap-Up (After Session 6)

### Step 1: Verify Sessions 0–6 all complete

Check this Work Journal conversation's running register: 7 entries (Sessions 0 + 1–6), each with verdict CLEAR or CONCERNS_RESOLVED.

If any session has unresolved CONCERNS or open ESCALATE, sprint is not complete; resolve before continuing.

### Step 2: Run post-sprint doc-sync

Open `argus/docs/sprints/synthesis-2026-04-26/post-sprint-doc-sync-prompt.md`. Open a fresh Claude Code session. Paste the prompt. Let it execute.

The post-sprint doc-sync handles:
- README.md count drift correction (19 protocols / 13 templates / 53 RULEs)
- Cross-reference final integrity sweep
- Argus deferred-items entry for boot-commit-logging automation
- Optional argus CLAUDE.md `## Rules` section (if Session 0 skipped it)

### Step 3: Run final verification sweep

Use the verification commands in `doc-update-checklist.md` Section E:

```bash
# E1: All session close-outs present (7 files)
ls argus/docs/sprints/synthesis-2026-04-26/session-{0,1,2,3,4,5,6}-closeout.md

# E2: README counts match reality
grep -E "[0-9]+ protocol\|[0-9]+ template\|[0-9]+ cross-project rule" argus/workflow/README.md

# E4: Regression checklist passes
# (Run R1 through R20 from regression-checklist.md §4 final time)

# E5: No open ESCALATEs
# (Verify in Work Journal running register)
```

### Step 4: Write sprint summary

Create `argus/docs/sprints/synthesis-2026-04-26/SPRINT-SUMMARY.md` covering:

- Sprint goal + outcome
- All 6 sessions: brief outcome, link to close-out, link to review
- Deliverables landed (cross-reference sprint-spec.md acceptance criteria)
- F1–F10 coverage (cross-reference Session 6 close-out's F1–F10 table)
- Workflow-version bumps applied
- Any deferred items (e.g., VERSIONING.md current-version reconciliation, bootstrap-index.md version header decision)
- Any escalations encountered + resolutions
- Submodule pointer SHAs (pre-sprint, post-sprint)

### Step 5: Mark sprint complete

In argus's CLAUDE.md "Active Sprint" section (or wherever your project tracks active sprints), mark synthesis-2026-04-26 as complete.

The next planning conversation can now reference this sprint's outputs as durable metarepo state. The new protocols (campaign-orchestration, operational-debrief), templates (stage-flow, scoping-session-prompt), and the expanded codebase-health-audit are auto-discoverable via `bootstrap-index.md` routing.

### Step 6: @reviewer subagent fallback note

If you used the @reviewer subagent fallback (manual review) at any point during the sprint, log it in the SPRINT-SUMMARY's "Notes" section. This helps future sprints understand the fallback's frequency + identify if subagent-invocation reliability needs investigation.

---

## Compaction Risk Per Session (informational)

| Session | Risk Score | Tier |
|---|---|---|
| 0 | 3 | LOW |
| 1 | 11 | MEDIUM |
| 2 | 12 | MEDIUM |
| 3 | 11 | MEDIUM |
| 4 | 9 | MEDIUM |
| 5 | 13 | MEDIUM (upper edge) |
| 6 | 11 | MEDIUM |

Scores match the per-session breakdowns in `session-breakdown.md`. All sessions are below the protocol's 14+ "must split" threshold. Session 5 is at the upper edge (3 new files created, multiple verification grep checks); if it or any other session shows compaction signals during execution (incomplete edits, contradictory changes, references to non-existent files), discard the session's commits and restart in a fresh conversation. C3 escalation criterion governs.

---

## Operator Acknowledgments Required Before Starting

Confirm:

- [ ] You've read this Work Journal Handoff document
- [ ] You've read the sprint-spec.md goal + scope sections
- [ ] You've read the spec-by-contradiction.md OUT-of-scope items
- [ ] The argus + workflow submodule are on `main` with clean working trees
- [ ] You have ~7.5 hours of operator-attended time available, splittable across days
- [ ] You have a Work Journal conversation open (or this document printed) for tracking session status
- [ ] You understand that this sprint is metarepo-only — no ARGUS runtime work expected

If any item is unconfirmed, resolve before starting Session 0.

---

## Quick Reference

- **Sprint package home:** `argus/docs/sprints/synthesis-2026-04-26/`
- **Metarepo home:** `argus/workflow/` (submodule)
- **Coordination surface:** This Work Journal conversation
- **Per-session implementation prompt:** `synthesis-2026-04-26-session-N-impl.md`
- **Per-session close-out (output):** `session-N-closeout.md`
- **Per-session review (output):** `session-N-review.md`
- **Final summary (post-sprint):** `SPRINT-SUMMARY.md`
- **Escalation triggers:** `escalation-criteria.md`
- **Cross-session invariants:** `regression-checklist.md`
- **OUT-of-scope items:** `spec-by-contradiction.md`

Begin with Session 0.
