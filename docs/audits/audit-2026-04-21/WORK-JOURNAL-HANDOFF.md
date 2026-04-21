# Work Journal Handoff — Audit 2026-04-21 Phase 3 Remediation

> ⚠️ **SUPERSEDED — 2026-04-21.** This handoff covers the audit track only. The audit Phase 3 has been absorbed into a larger campaign (Sprint 31.9 Health & Hardening) that also includes 2 impromptu sessions resolving bugs from the 2026-04-21 market session debrief.
>
> **Use [`docs/sprints/sprint-31.9/WORK-JOURNAL-HANDOFF.md`](../../sprints/sprint-31.9/WORK-JOURNAL-HANDOFF.md) as the canonical handoff for the Work Journal conversation.** That document covers both tracks (audit + impromptu) as a single coordinated campaign with one running register.
>
> This file remains for reference: it is the original audit-scoped handoff, kept to preserve the audit track's self-contained planning trail. The audit scope and stage plan in this file are all reflected unchanged in the superseding handoff.

---

> **Paste this as the opening message of a fresh Claude.ai conversation titled "Audit 2026-04-21 — Work Journal". Project knowledge: same as your normal ARGUS project (CLAUDE.md + bootstrap-index.md). This document tells the Work Journal chat what this campaign is, what it will receive, and what it must produce.**

---

## Campaign context

This is not a normal sprint — it is the **implementation phase of ARGUS's first-ever codebase audit** (Phase 3 of the audit campaign). Phase 1 (10 parallel auditor sessions) produced ~380 findings across the codebase. Phase 2 (operator triage) decided the disposition of each finding — 379 marked `fix-now`, grouped into 22 fix-session packages (`FIX-00` through `FIX-21`). Phase 3 executes those 22 packages across 8 stages.

Structurally this is implementation + close-out for a super-sized sprint. It follows your standard workflow (close-out skill per session, Tier 2 review per session, Work Journal as operational hub, final close-out per `templates/work-journal-closeout.md`) with the shape adjusted for 22 parallel-ish sessions instead of the typical 3–8 serial ones.

**Campaign identifier (for DEF/DEC attribution, commit messages, etc.):**
`audit-2026-04-21-phase-3`

---

## Baseline at kickoff (frozen — do not update this section)

| Item | Value |
|---|---|
| Date kicked off | 2026-04-21 |
| Sprint history close | 31.85 (Parquet cache consolidation, DEF-161 resolved) |
| Last Sprint commit | `dc91e1f` |
| pytest | 4,933 passed + 1 intermittent failure (DEF-150, time-of-day bug, NOT xdist race) |
| Vitest | 846 passed |
| Shadow variants in flight | 22 (across 10 patterns, pre-fingerprint-infra state) |
| Paper trading account | IBKR U24619949 |
| Known broken systems | Quality pipeline (catalyst_quality stuck at 50.0 per DEF-082; Sprint 32.9 weights/thresholds never reaching runtime per DEF-142); overflow.broker_capacity divergent (30 live vs 50 intended) |

Full baseline: `docs/audits/audit-2026-04-21/BASELINE.md`.

**Operator decisions made at kickoff:**

- **FIX-01 Option B selected** — extend `load_config()` to merge standalone `config/{section}.yaml` files over `system_live.yaml` blocks, precedence standalone > live > base. This is the structural fix for split-source config bugs. Opens a new DEC (next available — likely DEC-384). Auto-resolves FIX-02's overflow.yaml divergence as a side effect.

---

## The 8-stage plan

Each stage is a barrier: all sessions in the stage must commit before the next stage begins. Some stages run multiple sessions in parallel.

| Stage | Sessions | ARGUS state | Rationale |
|---|---|---|---|
| 1 | FIX-01, FIX-11, FIX-00, FIX-15, FIX-17, FIX-20 | DOWN | Priority tier (FIX-01 scoring pipeline + fingerprint infra) plus fringe disjoint sessions |
| 2 | FIX-02, FIX-03, FIX-19, FIX-12, FIX-21 | DOWN | FIX-02 applies Option B automatically; FIX-03 Rule-4 serial |
| 3 | FIX-04, FIX-16, FIX-14 | DOWN | FIX-04 Rule-4 serial (order_manager.py) |
| 4 | FIX-05, FIX-18, FIX-10 | DOWN | FIX-05 Rule-4 serial (risk_manager.py + orchestrator.py) |
| 5 | FIX-06, FIX-07 | DOWN | FIX-06 Rule-4 serial (universe_manager.py) |
| 6 | FIX-08 | DOWN | Solo — conflicts with remaining weekend groups |
| 7 | FIX-09 | DOWN | Solo — conflicts with FIX-13 test files |
| 8 | FIX-13 | **LIVE OK** | Test-hygiene fixes; includes DEF-150 root-cause fix (time-of-day bug, not xdist race) |

Full execution-plan rationale is in my earlier message in this conversation (and in the Phase 3 prompts directory).

---

## What you will receive during the campaign

For each of the 22 FIX sessions, I will paste TWO blocks into this conversation after the session commits:

### 1. Close-out report (from Claude Code implementation session)

Produced per `workflow/claude/skills/close-out.md`. Bracketed by `---BEGIN-CLOSE-OUT---` / `---END-CLOSE-OUT---` inside a fenced markdown code block. Includes:

- Session ID and date
- Self-assessment (CLEAN / MINOR_DEVIATIONS / FLAGGED)
- Change manifest (files added/modified/deleted + rationale)
- Judgment calls not pre-specified in the FIX-NN prompt
- Scope verification (per-finding status: DONE / PARTIAL / SKIPPED)
- Regression checks (the campaign-level ones: test delta ≥ 0, audit-report back-annotations applied, scope not exceeded, DEF closures recorded, DEF/DEC referenced in commit bullets)
- Test results (counts + command used)
- Unfinished work (if any)
- Notes for reviewer
- Followed by a `json:structured-closeout` JSON appendix (schema version 1.0)

### 2. Tier 2 review report (from `@reviewer` subagent, run after close-out)

Produced per `workflow/claude/skills/review.md`. Bracketed by `---BEGIN-REVIEW---` / `---END-REVIEW---` inside a fenced markdown code block. Includes:

- Verdict (CLEAR / CONCERNS / ESCALATE)
- Assessment summary table (scope compliance, close-out accuracy, test health, regression checklist, architectural compliance, escalation criteria)
- Findings organized by severity
- Recommendation
- Followed by a `json:structured-verdict` JSON appendix

---

## What this Work Journal conversation must do

### Per session (as reports come in)

When I paste a close-out + review pair, acknowledge receipt with a brief summary (2–4 lines) covering:

1. **Session ID + commit SHA(s)** — confirm the session landed
2. **Self-assessment + Tier 2 verdict** — e.g. "CLEAN / CLEAR" or "MINOR_DEVIATIONS / CONCERNS"
3. **Test delta** — baseline → post, net
4. **New items for the running register** (see below)
5. **Any flags** — if the review verdict is CONCERNS or ESCALATE, surface the specific concerns explicitly and ask me whether to address them mid-campaign (impromptu fix session) or defer (new DEF entry)

Do not produce prose longer than 4–6 lines per session summary. The running register (next section) is where cumulative detail lives.

### Running register (maintain throughout the campaign)

Keep a running list of:

#### DEF numbers assigned during the campaign

| DEF # | Description | Status | Source session |
|---|---|---|---|
| DEF-N | ... | OPEN / RESOLVED / added to CLAUDE.md | FIX-NN |

Mirror the format from `templates/work-journal-closeout.md`. Every DEF number mentioned in any close-out or review must be tracked here.

**Campaign-specific rule:** DEFs closed by this campaign (like DEF-082, DEF-142, DEF-089, and DEF-150 at Stage 8) must appear here with status `RESOLVED` and the FIX-NN session that closed them. New DEFs opened (e.g. from `read-only-no-fix-needed` findings promoted per step-4 routing, or from review reports flagging follow-ups) get added as `OPEN` with the session that added them. Note: DEF-161 (Parquet consolidation) was closed in Sprint 31.85 before the audit kickoff — it is NOT a campaign-closed DEF.

#### DEC entries tracked

| DEC # | Description | Session | Status |
|---|---|---|---|
| DEC-N | ... | FIX-NN | added to decision-log.md |

Expected DECs from this campaign: at minimum **DEC-384** for the Option B `load_config()` merge semantics. Possibly more if other sessions uncover architectural decisions (unlikely — most findings are cleanup).

#### Outstanding code-level items (not rising to DEF)

Per `templates/work-journal-closeout.md`: minor housekeeping items flagged in reviews or close-outs that are LOW/INFO severity and don't justify a dedicated DEF unless they persist past this campaign. Track location + severity + source session. At Stage 8 close, decide per item whether to (a) promote to DEF, (b) leave as "documented known-issues", or (c) drop.

#### Resolved items (no DEF needed — carry-forwards closed within campaign)

Per `templates/work-journal-closeout.md`: items noted in an earlier session that got fixed in a later session. Prevents double-counting at close-out.

#### Outstanding review flags

Any CONCERNS or ESCALATE verdicts I have not yet triaged. Resolved entries stay in the register with a resolution note so I have audit trail.

### At Stage 8 close (final close-out)

When I tell you "Stage 8 complete, generate the campaign close-out":

1. Produce a **filled-in doc-sync automation prompt** per `templates/work-journal-closeout.md` human-in-the-loop mode. Embed the campaign close-out data directly inside that doc-sync prompt (don't produce a separate intermediate artifact).
2. The embedded close-out data must cover:
   - Sprint summary (campaign identifier, session list, test deltas)
   - DEF numbers assigned (canonical list for doc-sync to use)
   - DEC numbers tracked
   - Resolved items (to prevent doc-sync from creating DEF entries for them)
   - Outstanding code-level items (for Known Issues section of docs)
   - Corrections needed in any initial doc-sync patch
3. In addition to the doc-sync-embedded close-out, produce a standalone narrative section covering:
   - What went smoothly vs. what surprised me
   - How Option B played out in practice (FIX-01 landing + FIX-02 auto-resolution + any downstream implications)
   - How the scoring-context fingerprint separation worked for the 22 shadow variants
   - Any stages that deviated from the plan (parallelism that didn't work, rebases that conflicted, etc.)
   - Sprint 31B readiness assessment (is post-audit main ready for Research Console work?)

The narrative section is what I'll use to draft the final CLAUDE.md update and to plan Sprint 31B.

---

## Campaign-level regression checklist

Every FIX session's close-out will evaluate this checklist (the reports I paste will include the results):

- [ ] pytest net delta ≥ 0 against baseline (4,933 passed; FIX-01 expected to add +4, others ≥ 0)
- [ ] DEF-150 flake remains the only pre-existing failure (or is fixed by FIX-13 at Stage 8)
- [ ] No file outside the session's declared Scope was modified
- [ ] Every finding resolved by the session was back-annotated in the Phase 1 audit report with `**RESOLVED FIX-NN**`
- [ ] Every DEF closure was recorded in CLAUDE.md
- [ ] Every new DEF/DEC number was referenced in the commit message bullets
- [ ] For `read-only-no-fix-needed` findings: verification command + output recorded, or DEF promoted
- [ ] For `deferred-to-defs` findings: suggested fix applied AND DEF-NNN added to CLAUDE.md

Flag any session where ≥2 checklist items fail.

---

## Campaign-level escalation criteria

Trigger ESCALATE verdict (and I get a direct mention asking how to proceed) if any of the following appear in a Tier 2 review:

- Any CRITICAL severity finding in the review
- pytest net delta < 0
- Scope boundary violation: files outside the Scope section were modified
- DEF-150 flake not present AND a different test failure surfaces (indicates real regression)
- Rule-4 sensitive file touched by a session not authorized to touch it (rare — the stage plan prevents this)
- Audit-report back-annotation missing or incorrect (would compromise audit trail)
- FIX-01's Step 1G fingerprint checkpoint fails before pipeline edits proceed

Non-escalation deviations (CONCERNS verdict, acknowledged-and-logged):
- Minor judgment calls inside session scope
- One-off DEF-150 flake hits
- Cosmetic findings where the suggested fix diverged from what actually landed
- Architectural observations worth tracking but not blocking

---

## Tone and format

- Keep per-session summaries tight (2–6 lines). The running register is cumulative; don't repeat in the per-session summary what the register already holds.
- Use the exact DEF-NNN and FIX-NN notation throughout — these are canonical identifiers.
- When I ask "status?" mid-campaign, respond with: sessions committed, open review concerns, outstanding DEFs opened this campaign, next stage.
- When a session report includes judgment calls that affect the campaign (not just the session), flag those explicitly and ask how to proceed.
- Default tone: terse, technical, precise. Match Steven's communication style from project knowledge.

---

## Ready state

At this point, reply with:
1. Acknowledgement that you've ingested this handoff
2. An empty running register (DEFs assigned table with no rows; DECs table with no rows; etc.)
3. "Awaiting Stage 1 session reports" as the last line

I will then paste the close-out + review blocks from each Stage 1 session as they complete.
