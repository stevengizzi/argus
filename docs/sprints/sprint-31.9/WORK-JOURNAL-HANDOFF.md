# Work Journal Handoff — Sprint 31.9 Health & Hardening Campaign

> **Paste this as the opening message of a fresh Claude.ai conversation titled "Sprint 31.9 — Work Journal". Project knowledge: same as your normal ARGUS project (CLAUDE.md + bootstrap-index.md). This document tells the Work Journal chat what this campaign is, what it will receive, and what it must produce.**

> **This handoff supersedes `docs/audits/audit-2026-04-21/WORK-JOURNAL-HANDOFF.md`.** That older handoff covers the audit track only. Use THIS handoff for the full campaign (audit Phase 3 + debrief impromptu).

---

## Campaign context

Sprint 31.9 is a **coordinated multi-session campaign** with two tracks:

### Track A — Audit Phase 3 (22 sessions, pre-scoped)
Implementation phase of ARGUS's first codebase audit. Phase 1 (10 parallel auditor sessions) produced ~380 findings. Phase 2 (operator triage) grouped them into 22 fix-session packages `FIX-00` through `FIX-21`. Phase 3 executes those packages across 8 stages. Session prompts live in `docs/audits/audit-2026-04-21/phase-3-prompts/`.

### Track B — Debrief Impromptu (2 sessions + placeholder)
Resolves bugs discovered during the 2026-04-21 market session that are **not** covered by audit Phase 3. The market session debrief is at `docs/debriefs/2026-04-21.md`. Session prompts live in `docs/sprints/sprint-31.9/`:
- `impromptu-01-log-ui-hygiene.md` — safe-during-trading, resolves F-01 / F-05 / F-06 / F-08
- `impromptu-02-scoping.md` — read-only investigation of bracket amendment leak (F-03, F-04, F-10)
- `impromptu-02-fix.md` — placeholder; generated after IMPROMPTU-02 scoping completes

**Campaign identifier (for DEF/DEC attribution, commit messages, etc.):**
`sprint-31.9-health-and-hardening`

Campaign README: `docs/sprints/sprint-31.9/README.md`
Stage-flow DAG: `docs/sprints/sprint-31.9/STAGE-FLOW.md` — **consult this for dependency reasoning when the Work Journal needs to determine what may run when, or when deciding how to respond to a stage-level issue.**

---

## Baseline at kickoff (frozen — do not update this section)

| Item | Value |
|---|---|
| Date kicked off | 2026-04-21 |
| Sprint history close | 31.85 (Parquet cache consolidation, DEF-161 resolved) |
| Last sprint commit | `dc91e1f` |
| pytest | 4,933 passed + 1 intermittent failure (DEF-150, time-of-day bug — NOT xdist race) |
| Vitest | 846 passed |
| Shadow variants in flight | 22 (across 10 patterns, pre-fingerprint-infra state) |
| Paper trading account | IBKR U24619949 |
| Known broken systems | Quality pipeline (DEF-082, DEF-142 — resolved by FIX-01); overflow.broker_capacity divergent 30 live vs 50 intended (resolved by FIX-02) |

Full baseline: `docs/audits/audit-2026-04-21/BASELINE.md`.

**Operator decisions made at kickoff:**

- **FIX-01 Option B selected** — extend `load_config()` to merge standalone `config/{section}.yaml` files over `system_live.yaml` blocks, precedence standalone > live > base. Opens new DEC (likely `DEC-384`). Auto-resolves FIX-02's overflow.yaml divergence as side effect.

---

## The 9-stage plan

> Full DAG, dependency rationale, and parallelization notes: **[STAGE-FLOW.md](./STAGE-FLOW.md)**.
> The table below is a condensed operational reference. If the DAG diagram and this table ever drift, STAGE-FLOW.md is authoritative.

Each stage is a barrier: all sessions in the stage must commit before the next stage begins. Some stages run multiple sessions in parallel.

| Stage | Sessions | ARGUS state | Rationale |
|---|---|---|---|
| 1 | FIX-01, FIX-11, FIX-00, FIX-15, FIX-17, FIX-20 | DOWN | Priority tier (FIX-01 scoring pipeline + fingerprint infra) plus fringe disjoint sessions |
| 2 | FIX-02, FIX-03, FIX-19, FIX-12, FIX-21 | DOWN | FIX-02 applies Option B automatically; FIX-03 Rule-4 serial |
| 3 | FIX-04, FIX-16, FIX-14 | DOWN | FIX-04 Rule-4 serial (order_manager.py). **FIX-04 commit unlocks Stage 9A eligibility.** |
| 4 | FIX-05, FIX-18, FIX-10 | DOWN | FIX-05 Rule-4 serial (risk_manager.py + orchestrator.py) |
| 5 | FIX-06, FIX-07 | DOWN | FIX-06 Rule-4 serial (universe_manager.py) |
| 6 | FIX-08 | DOWN | Solo — conflicts with remaining weekend groups |
| 7 | FIX-09 | DOWN | Solo — conflicts with FIX-13 test files |
| 8 | FIX-13, IMPROMPTU-01 | **LIVE OK** | Test hygiene (FIX-13 closes DEF-150) + log/UI hygiene (IMPROMPTU-01). Both safe-during-trading. No file overlap. |
| 9A | IMPROMPTU-02 scoping | READ-ONLY | Eligible post-Stage-3 (parallel to Stages 4–8 OK). Writes only `docs/sprints/sprint-31.9/`. Produces findings report + fix prompt. |
| 9B | IMPROMPTU-02 fix | DOWN | Weekend-only. Requires both Stage 8 and Stage 9A complete. |

**Cross-track ordering constraints** (full dependency list in [STAGE-FLOW.md](./STAGE-FLOW.md) "Hard mandatory edges" table):

- IMPROMPTU-02 scoping reads `argus/execution/order_manager.py` and must read it **after FIX-04 lands** (Stage 3). This prevents conflating F-02's symptoms (`entry_price=0` from getattr bug) with F-03's symptoms (bracket amendment leak).
- IMPROMPTU-01 touches `argus/ui/src/features/trades/ShadowTradesTab.tsx` (UI unit fix for F-06) and `argus/strategies/pattern_strategy.py` (F-01 log level). No overlap with FIX-13 test files. Both run in Stage 8 in parallel.
- IMPROMPTU-02 fix (Stage 9B) is weekend-only and must land on a main that has both FIX-04 applied (Stage 3) and IMPROMPTU-02 scoping complete (Stage 9A).

---

## What you will receive during the campaign

For each of the 24 sessions (22 FIX + 2 IMPROMPTU), I will paste TWO blocks into this conversation after the session commits:

### 1. Close-out report (from Claude Code implementation session)

Produced per `workflow/claude/skills/close-out.md`. Bracketed by `---BEGIN-CLOSE-OUT---` / `---END-CLOSE-OUT---` inside a fenced markdown code block. Includes:

- Session ID and date
- Self-assessment (CLEAN / MINOR_DEVIATIONS / FLAGGED)
- Change manifest (files added/modified/deleted + rationale)
- Judgment calls not pre-specified in the session prompt
- Scope verification (per-finding status: DONE / PARTIAL / SKIPPED)
- Regression checks (test delta ≥ 0, scope not exceeded, DEF closures recorded, DEF/DEC referenced in commit bullets). Audit sessions also verify audit-report back-annotations.
- Test results (counts + command used)
- Unfinished work (if any)
- Notes for reviewer
- Followed by a `json:structured-closeout` JSON appendix (schema version 1.0)

**Special cases:**
- **IMPROMPTU-02 scoping** is read-only — it produces a findings report at `docs/sprints/sprint-31.9/impromptu-02-findings.md` and a fix prompt at `docs/sprints/sprint-31.9/impromptu-02-fix.md` (replacing the placeholder). No Tier 2 review needed — just a scope-verification note that no code or non-investigation files were modified.
- **IMPROMPTU-01 and IMPROMPTU-02 fix** follow the full close-out + Tier 2 review pattern.

### 2. Tier 2 review report (from `@reviewer` subagent, run after close-out)

Produced per `workflow/claude/skills/review.md`. Bracketed by `---BEGIN-REVIEW---` / `---END-REVIEW---` inside a fenced markdown code block. Same schema as the audit track.

---

## What this Work Journal conversation must do

### Per session (as reports come in)

When I paste a close-out + review pair, acknowledge receipt with a brief summary (2–4 lines) covering:

1. **Session ID + commit SHA(s)** — confirm the session landed
2. **Self-assessment + Tier 2 verdict** — e.g. "CLEAN / CLEAR"
3. **Test delta** — baseline → post, net
4. **New items for the running register** (see below)
5. **Any flags** — if the review verdict is CONCERNS or ESCALATE, surface the specific concerns and ask me whether to address them mid-campaign or defer

Keep per-session summaries to 4–6 lines. Cumulative detail lives in the register below.

### Running register (maintain throughout the campaign)

#### DEF numbers assigned during the campaign

| DEF # | Description | Status | Source session |
|---|---|---|---|
| DEF-N | ... | OPEN / RESOLVED / added to CLAUDE.md | FIX-NN or IMPROMPTU-NN |

Mirror the format from `workflow/templates/work-journal-closeout.md`. Every DEF number mentioned in any close-out or review must be tracked here.

**Campaign-specific rule:** DEFs closed by this campaign (DEF-082, DEF-142, DEF-089, DEF-150 at Stage 8, plus Track-B DEFs) must appear with status `RESOLVED` and the session that closed them. New DEFs opened (e.g. from `read-only-no-fix-needed` findings promoted, or from review reports flagging follow-ups, or from IMPROMPTU-02 scoping) get added as `OPEN`.

Note: DEF-161 (Parquet consolidation) was closed in Sprint 31.85 *before* the campaign — NOT a campaign-closed DEF.

#### DEC entries tracked

| DEC # | Description | Session | Status |
|---|---|---|---|
| DEC-N | ... | FIX-NN or IMPROMPTU-NN | added to decision-log.md |

Expected DECs from this campaign:
- **DEC-384 (pre-allocated)** — FIX-01 Option B `load_config()` merge semantics
- Possibly more from IMPROMPTU-02 if the bracket-amendment root cause warrants an architectural decision (e.g., "bracket amendment no longer cancels and re-places; only shifts stop price via IBKR order-modification API")

#### Outstanding code-level items (not rising to DEF)

Per `workflow/templates/work-journal-closeout.md`: minor housekeeping items flagged in reviews or close-outs that are LOW/INFO severity. Track location + severity + source session. At campaign close, decide per item whether to (a) promote to DEF, (b) leave as "documented known-issues", or (c) drop.

#### Resolved items (no DEF needed — carry-forwards closed within campaign)

Items noted in an earlier session that got fixed in a later session. Prevents double-counting at close-out.

#### Outstanding review flags

Any CONCERNS or ESCALATE verdicts I have not yet triaged. Resolved entries stay in the register with a resolution note.

### At Stage 9B close (final campaign close-out)

When I tell you "Stage 9B complete, generate the campaign close-out":

1. Produce a **filled-in doc-sync automation prompt** per `workflow/templates/work-journal-closeout.md` human-in-the-loop mode. Embed the campaign close-out data directly inside that doc-sync prompt.

2. The embedded close-out data must cover:
   - Campaign summary (identifier, all 24 sessions with their commit SHAs, test deltas)
   - DEF numbers assigned (canonical list for doc-sync)
   - DEC numbers tracked
   - Resolved items (to prevent doc-sync from creating DEF entries for them)
   - Outstanding code-level items (for Known Issues section of docs)
   - Corrections needed in any initial doc-sync patch

3. In addition to the doc-sync-embedded close-out, produce a standalone narrative section covering:
   - What went smoothly vs. what surprised me
   - How Option B played out in practice (FIX-01 landing + FIX-02 auto-resolution)
   - How the scoring-context fingerprint separation worked for the 22 shadow variants
   - **Bracket amendment root cause** — summarize what IMPROMPTU-02 scoping found and what IMPROMPTU-02 fix changed
   - **Paper-trading data quality** — given F-02 + F-03 + F-04 corruption discovered on April 21, should data from pre-campaign sessions be flagged as degraded for CounterfactualTracker promotion purposes? Recommend yes/no + scope.
   - Any stages that deviated from the plan
   - Sprint 31B readiness assessment

4. Update `docs/sprints/sprint-31.9/README.md` status line to `COMPLETE — <final commit SHA>`.

5. Update `docs/debriefs/2026-04-21.md` — add a resolution section at the bottom listing which findings were fixed in which session + commit.

---

## Campaign-level regression checklist

Every session's close-out will evaluate this checklist:

- [ ] pytest net delta ≥ 0 against baseline (4,933 passed at kickoff; FIX-01 expected to add +4; others ≥ 0)
- [ ] DEF-150 flake remains the only pre-existing failure (or is fixed by FIX-13 at Stage 8)
- [ ] No file outside the session's declared Scope was modified
- [ ] **Audit sessions only:** Every finding resolved was back-annotated in the Phase 1 audit report with `**RESOLVED FIX-NN**`
- [ ] Every DEF closure recorded in CLAUDE.md
- [ ] Every new DEF/DEC number referenced in commit message bullets
- [ ] **Audit sessions only:** For `read-only-no-fix-needed` findings — verification command + output recorded, or DEF promoted
- [ ] **Audit sessions only:** For `deferred-to-defs` findings — suggested fix applied AND DEF-NNN added to CLAUDE.md

Flag any session where ≥2 checklist items fail.

---

## Campaign-level escalation criteria

Trigger ESCALATE verdict (and I get a direct mention asking how to proceed) if any of the following appear:

- Any CRITICAL severity finding in the review
- pytest net delta < 0
- Scope boundary violation: files outside the Scope section modified
- DEF-150 flake not present AND a different test failure surfaces (indicates real regression)
- Rule-4 sensitive file touched by a session not authorized to touch it
- Audit-report back-annotation missing or incorrect
- FIX-01's Step 1G fingerprint checkpoint fails before pipeline edits proceed
- **IMPROMPTU-02 scoping** reveals bracket amendment is fundamentally more complex than the F-03 hypothesis (e.g., multiple intertwined bugs, not one root cause) — escalate to decide whether to split into multiple fix sessions

Non-escalation deviations (CONCERNS verdict, acknowledged-and-logged):
- Minor judgment calls inside session scope
- One-off DEF-150 flake hits
- Cosmetic findings where the suggested fix diverged from what landed
- Architectural observations worth tracking but not blocking

---

## Tone and format

- Keep per-session summaries tight (2–6 lines). Running register is cumulative.
- Use exact `DEF-NNN`, `DEC-NNN`, `FIX-NN`, `IMPROMPTU-NN` notation — these are canonical identifiers.
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
