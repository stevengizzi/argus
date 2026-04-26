# Sprint synthesis-2026-04-26, Session 4: operational-debrief.md + Bootstrap Routing

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.**

2. **Verify Sessions 0–3 have landed:**
   ```bash
   # Session 0
   grep -c "^- \*\*P2[6789] candidate:\*\*" argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md
   # Must return 4

   # Session 1
   grep -c "^RULE-051:\|^RULE-052:\|^RULE-053:" argus/workflow/claude/rules/universal.md
   # Must return 3

   # Session 2
   grep -c "^**Synthesis status:**" argus/workflow/evolution-notes/2026-04-21-*.md | wc -l
   # Must return 3

   # Session 3
   ls argus/workflow/protocols/campaign-orchestration.md
   # Must exist
   grep -c "## Two-Session Scoping Variant" argus/workflow/protocols/impromptu-triage.md
   # Must return ≥ 1
   ```
   If any check fails, **HALT and report** (escalation criterion D1).

3. Read these files to load context:
   - `argus/docs/sprints/synthesis-2026-04-26/review-context.md`
   - `argus/workflow/evolution-notes/2026-04-21-debrief-absorption.md` (the primary source for debrief patterns)
   - `argus/docs/protocols/market-session-debrief.md` (the ARGUS-specific debrief implementation; you'll be lifting the abstract pattern from it without copying ARGUS-specific content)
   - `argus/workflow/protocols/campaign-orchestration.md` (created in Session 3; you'll be cross-referencing its §1 debrief-absorption discussion)
   - `argus/workflow/bootstrap-index.md` (you'll be adding 1 routing entry + 1 Protocol Index row)

4. Verify clean working tree.

## Objective

Land the second new protocol of the sprint plus its bootstrap-routing wiring. This protocol covers the abstract pattern of recurring-event-driven knowledge streams (operational debriefs, post-incident reviews, periodic reviews) — the metarepo-level abstraction of which ARGUS's `market-session-debrief.md` is one project-specific instance.

The protocol explicitly does NOT codify the rejected safety-tag taxonomy (4-tag flat or core+modifier — see escalation criterion B3). Instead, it codifies the **execution-anchor-commit correlation** pattern that replaces it. Phase A pushback round 2 established that mechanism via Sprint 31.9 execution evidence: the operator records the boot/execution-anchor commit at session start; the debrief uses the commit-pair (start, end) as the audit trail rather than safety tags as the routing mechanism.

## Requirements

This session is structured into 3 sub-phases.

### Sub-Phase 1: Create operational-debrief.md skeleton + 3 recurring-event patterns

Create the new file at `argus/workflow/protocols/operational-debrief.md`. The file is borderline-large (~150–200 lines expected). Structure:

```markdown
<!-- workflow-version: 1.0.0 -->
<!-- last-updated: 2026-04-26 -->

# Operational Debrief

A **recurring-event-driven knowledge stream** is a series of related debriefs/reviews/retrospectives produced at predictable cadence — sometimes periodic (e.g., daily, weekly), sometimes event-driven (e.g., post-incident, post-deployment), sometimes mid-event without a fixed cycle (e.g., quarterly architectural review). The stream accumulates project knowledge that's expensive to recover if any individual debrief is lost.

This protocol covers the abstract pattern. Project-specific debrief implementations (e.g., ARGUS's `market-session-debrief.md`, a deployment runbook's post-deploy retrospective, a service ops team's weekly health review) instantiate the pattern with project-specific roles, schedules, and artifacts. This metarepo protocol provides the abstraction; project-specific protocols handle the concretes.

For absorbing debrief findings into ongoing campaign work, see `protocols/campaign-orchestration.md` §1 (Campaign Absorption). Absorption is the read-side of the recurring-event-driven stream — what the campaign does with the findings the debrief produces.

## When This Protocol Applies

Apply when the project produces recurring debriefs/reviews/retrospectives that:
- Generate findings that must be acted on (DEFs, deferred items, judgment calls).
- Need to be correlated with the underlying execution state (which version was running, which deployment, which build).
- Accumulate over time into a knowledge stream (the Nth debrief references the (N-1)th's findings).

If the project produces only ad-hoc retrospectives (no cadence, no accumulating stream), use `protocols/sprint-planning.md` Phase A or `protocols/impromptu-triage.md` directly.

## 1. Three Recurring-Event Patterns

Recurring-event-driven knowledge streams come in three shapes. Identify which shape applies before adopting the pattern's machinery.

### 1.1 Periodic Operational Debrief

**Cadence:** Fixed, calendar-driven (daily, weekly, monthly).
**Trigger:** Time elapsed.
**Examples:**
- A trading system's daily post-market debrief covering the trading session's execution.
- An e-commerce service's weekly health review covering uptime, latency p99, error rates.
- A SaaS platform's monthly architectural review covering tech-debt accumulation, hotspot files, deferred refactors.

**Characteristic shape:** Each debrief covers a fixed time window. The debrief's audit trail is correlated with execution-anchor commits at the start and end of the window. The debrief produces findings that the next campaign or sprint absorbs.

### 1.2 Event-Driven Debrief

**Cadence:** Variable, event-driven.
**Trigger:** A specific event occurs (deployment, incident, customer escalation, regulatory event).
**Examples:**
- A post-incident review covering the SEV-1 outage on YYYY-MM-DD.
- A post-deployment retrospective covering the v2.7.0 release.
- A customer-escalation review covering the enterprise-customer ticket #XXX.

**Characteristic shape:** Each debrief covers the event scope (typically a window from "X minutes before symptom" to "X minutes after resolution"). The debrief's audit trail is correlated with the event-anchor (deployment SHA, incident timestamp, ticket ID). The debrief produces findings the next campaign absorbs OR a follow-on incident-prevention sprint takes on directly.

### 1.3 Periodic Review Without a Cycle

**Cadence:** Mid-event, no fixed cycle.
**Trigger:** Operator judgment that a review is due (architectural drift visible, tech-debt threshold exceeded, etc.).
**Examples:**
- A quarterly-ish architecture review (no fixed quarter; runs when operator judgment says due).
- A pre-fundraise codebase audit.
- A pre-acquisition due-diligence review.

**Characteristic shape:** Each review covers the project's current state at the review's start. The audit trail is correlated with the execution-anchor commit at review start (no end commit; the review IS the work). The review produces findings that often spawn a synthesis sprint or strategic check-in.

## 2. Execution-Anchor Commit Correlation

Each debrief in a recurring-event-driven stream MUST correlate its findings with an **execution-anchor commit** — a SHA that uniquely identifies the project state the findings apply to.

**For periodic debriefs (§1.1):** the anchor is typically a pair (start_commit, end_commit). The start_commit is the project's HEAD at the start of the time window; end_commit is HEAD at the end.

**For event-driven debriefs (§1.2):** the anchor is a single SHA — the deployment SHA, the SHA running at the time of the incident, the SHA in production at the time of the customer escalation.

**For periodic-without-cycle reviews (§1.3):** the anchor is the SHA at review start.

The execution-anchor commit is the **audit trail mechanism**. When a future sprint absorbs the debrief's findings, the sprint cites the anchor commit + the relevant code paths. If a finding turns out to be wrong (per `protocols/campaign-orchestration.md` §7 DEBUNKED status), the correction cites the anchor commit too — making the correction's scope explicit.

Recording the anchor commit is **operator-led**. The operator manually notes the SHA at debrief start (e.g., copies HEAD into the debrief document's metadata block).

**Recommended automation: project-specific.** Live systems with continuously-running daemons can write the anchor commit to a known path at startup (e.g., a daemon writing `logs/boot-history.jsonl` with one line per startup containing timestamp + SHA + brief metadata). Whether to automate, where to log to, and what additional metadata to capture is a project-specific decision — the metarepo doesn't prescribe.

For ARGUS's specific implementation of automation, see ARGUS's deferred-items list (the boot-commit-logging automation is tracked there).

<!-- Origin: synthesis-2026-04-26 evolution-note-2 (debrief-absorption) +
     Phase A pushback round 2. The 4-tag safety taxonomy was empirically
     overruled during ARGUS Sprint 31.9: the operator ran fixes during
     active market sessions regardless of tag, using the boot-commit-pair
     correlation as the actual audit-trail mechanism. The execution-
     anchor-commit pattern formalizes that mechanism. -->

## 3. Three Non-Trading Examples

The metarepo intentionally avoids ARGUS-specific terminology. The pattern applies broadly. Three non-trading instantiations:

### 3.1 Deployment Retrospective (Event-Driven)

A SaaS platform deploys v2.7.0 at 14:32 UTC. The post-deployment retrospective runs the next morning, covering the deployment window. Findings:
- The new feature flag rollout had unintended cache-invalidation effects in the staging environment.
- Three customers reported intermittent 502s in the first hour post-deploy.
- The deployment script's pre-deploy migration step took 11 minutes (vs the 4-minute baseline).

**Execution-anchor commit:** `<v2.7.0 SHA>`. All findings reference this SHA + relevant file paths.

### 3.2 Post-Incident Review (Event-Driven)

A payments service experiences a SEV-1 outage at 09:14 UTC affecting 3% of transactions for 47 minutes. The post-incident review runs that afternoon. Findings:
- The root cause was a connection-pool exhaustion under unexpected load.
- The service's monitoring did not page until 11 minutes after symptom onset.
- The runbook's "restart the database connection pool" instruction was missing the hold-flag prerequisite.

**Execution-anchor commit:** `<SHA running at 09:14 UTC>`. The runbook-fix follow-on sprint cites this SHA when adding the hold-flag prerequisite.

### 3.3 Weekly Health Review (Periodic)

A 4-person backend team runs a Monday-morning weekly health review. The review covers the prior week's deploys (12), open Sentry alerts (4), p99 latency drift (within bounds), and tech-debt items added (2). Findings:
- An open Sentry alert from 4 days ago is still un-investigated.
- The 02:00 UTC scheduled task had 2 failures during the week (vs typical 0).
- The migration scheduled for next week needs a pre-check on table sizes.

**Execution-anchor commits:** start (Monday previous week's HEAD) and end (Monday this week's HEAD). All findings reference both SHAs (e.g., the Sentry alert was raised against the Wednesday-mid-week SHA — that SHA is recorded in the alert; the review references it).

## 4. Cross-References

- `protocols/campaign-orchestration.md` §1 — how the campaign absorbs debrief findings.
- `protocols/sprint-planning.md` — when a debrief's findings spawn a planning conversation.
- `protocols/impromptu-triage.md` — when a debrief's findings warrant an immediate impromptu sprint vs. queueing.

## 5. Project-Specific Implementations

This metarepo protocol is the abstract pattern. Project-specific protocols document the concrete cadence, roles, artifacts, and tooling. Examples:

- **ARGUS** (`docs/protocols/market-session-debrief.md`): periodic operational debrief covering the daily trading session. Cadence: daily, post-market. Anchor: boot-commit pair (start, end). Findings: DEFs, candidate retrospective patterns. Absorbs into the next sprint or campaign.

Other projects following this pattern would have their own project-specific protocol documenting their cadence + roles + artifacts.
```

This is the full content. Adjust prose as needed for fluency, but preserve all numbered sections, all Origin footnotes, and all cross-references.

**Verification:**
```bash
ls argus/workflow/protocols/operational-debrief.md
# Expected: file exists

grep -c "^## [1-5]\|^### [1-5]\.[1-3]" argus/workflow/protocols/operational-debrief.md
# Expected: ≥ 5 (5 top-level sections + at least the 3 sub-sections in §1)

grep -c "execution-anchor commit" argus/workflow/protocols/operational-debrief.md
# Expected: ≥ 4 (per F3 generalized terminology — used as the primary term)

grep -c "boot commit" argus/workflow/protocols/operational-debrief.md
# Expected: ≤ 2 (used as one example/legacy term, not as universal)

# F2 recurring-event-driven framing
grep -c "periodic\|event-driven\|recurring" argus/workflow/protocols/operational-debrief.md
# Expected: ≥ 5

# 3 non-trading examples (F2 expanded)
grep -c "^### 3\.[123]" argus/workflow/protocols/operational-debrief.md
# Expected: 3

# Origin footnote
grep -c "Origin: synthesis-2026-04-26" argus/workflow/protocols/operational-debrief.md
# Expected: ≥ 1 (the §2 footnote consolidates the rationale)
```

### Sub-Phase 2: Verify operational-debrief.md content quality

Before moving to Sub-Phase 3, run these content-quality checks:

1. **F2 recurring-event-driven framing:** §1 has all 3 patterns (periodic, event-driven, periodic-without-cycle); each has at least 1 worked example.
2. **F3 execution-anchor-commit terminology:** "execution-anchor commit" is the primary term; "boot commit" appears only as one example.
3. **F2 expanded with 3 non-trading concrete examples:** §3 has deployment retrospective, post-incident review, weekly health review (NOT trading-session debrief). Note: the canonical F5 finding (3 non-trading *fingerprint* examples) belongs to Session 6's audit §3.3 (pricing engine, A/B test, ML model) — distinct from these debrief-pattern examples.
4. **No safety-tag taxonomy:** verify zero matches for the 4 rejected tags.
5. **Cross-reference to campaign-orchestration §1** is present.
6. **ARGUS reference** is in §5 as one example, not as the universal pattern. ARGUS-specific terminology ("DEF," "trading session") appears only in the §5 ARGUS-specific bullet, not in §§1–4.

If any check fails, fix in-session before moving to Sub-Phase 3.

### Sub-Phase 3: Bootstrap-index routing entry

In `argus/workflow/bootstrap-index.md`:

**Add a new "Conversation Type → What to Read" entry:**

```markdown
- **Operational Debrief / Post-Incident Review / Periodic Review** — read `protocols/operational-debrief.md` for the abstract pattern covering periodic operational debriefs, event-driven debriefs, and periodic-without-cycle reviews. Cross-reference `protocols/campaign-orchestration.md` §1 for absorbing debrief findings into ongoing campaigns. Project-specific debrief protocols (e.g., ARGUS's `docs/protocols/market-session-debrief.md`) instantiate this abstract pattern.
```

**Add a new Protocol Index row:**

```markdown
| `protocols/operational-debrief.md` | Recurring-event-driven knowledge streams (periodic / event-driven / periodic-without-cycle); execution-anchor-commit correlation pattern. | 1.0.0 |
```

**Verification:**
```bash
grep -c "Operational Debrief" argus/workflow/bootstrap-index.md
# Expected: ≥ 1

grep -c "operational-debrief\.md" argus/workflow/bootstrap-index.md
# Expected: ≥ 1

# Verify existing entries (including Session 3's campaign-orchestration entry) unchanged
git diff HEAD argus/workflow/bootstrap-index.md | grep "^<" | grep -v "^---"
# Expected: empty (no deletions; only additions)

# Verify Session 3's campaign-orchestration entry still present
grep -c "campaign-orchestration\.md" argus/workflow/bootstrap-index.md
# Expected: ≥ 1 (preserved from Session 3)
```

## Constraints

- **Do NOT modify** any path under `argus/argus/`, `argus/tests/`, `argus/config/`, `argus/scripts/`. Triggers escalation criterion A1.
- **Do NOT modify** Sessions 0/1/2/3 outputs. They are stable.
- **Do NOT use** safety-tag taxonomy (4-tag flat or core+modifier) anywhere in `operational-debrief.md`. The pattern is rejected. Reintroduction triggers escalation criterion B3.
- **Do NOT use** ARGUS-specific terminology ("DEF," "trading session," "post-market") universally. Generalized terminology per F2/F3/F5. ARGUS-specific terms are acceptable ONLY in §5 as one project-specific example. Triggers escalation criterion B4 if missed.
- **Do NOT create** `templates/scoping-session-prompt.md` (Session 5's job).
- **Do NOT modify** `protocols/campaign-orchestration.md` (Session 3's output, stable).

## Test Targets

No executable code, no tests. Verification is grep-based.

## Definition of Done

- [ ] Sub-Phase 1: `protocols/operational-debrief.md` exists; workflow-version 1.0.0; 5 sections + 3 sub-sections in §1 + 3 examples in §3
- [ ] Sub-Phase 2: F2 + F3 generalized-terminology checks pass
- [ ] Sub-Phase 3: `bootstrap-index.md` has new Operational Debrief routing + Protocol Index row; existing entries (including Session 3's campaign-orchestration) unchanged
- [ ] All verification grep + diff commands run; outputs captured
- [ ] No scope creep
- [ ] Close-out report at `argus/docs/sprints/synthesis-2026-04-26/session-4-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Sessions 0–3 outputs untouched | `git diff HEAD --name-only -- argus/workflow/claude/ argus/workflow/templates/ argus/workflow/scaffold/ argus/workflow/evolution-notes/ argus/workflow/protocols/campaign-orchestration.md argus/workflow/protocols/impromptu-triage.md` returns empty |
| ARGUS runtime untouched | `git diff HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/` returns empty |
| Bootstrap-index existing entries preserved | `git diff HEAD argus/workflow/bootstrap-index.md \| grep "^<"` returns empty |
| F2 recurring-event-driven framing | §1 of operational-debrief.md has all 3 patterns |
| F3 execution-anchor-commit terminology | `grep "execution-anchor commit" argus/workflow/protocols/operational-debrief.md \| wc -l` ≥ 4 |
| 3 non-trading examples | §3 has deployment retrospective + post-incident review + weekly health review |
| No safety-tag taxonomy | `grep -E "safe-during-trading\|weekend-only\|read-only-no-fix-needed\|deferred-to-defs" argus/workflow/protocols/operational-debrief.md` returns empty |
| Cross-reference to campaign-orchestration §1 | `grep "campaign-orchestration\.md" argus/workflow/protocols/operational-debrief.md` returns ≥ 1 |
| Workflow-version on new file | `head -3 argus/workflow/protocols/operational-debrief.md` shows `<!-- workflow-version: 1.0.0 -->` |

## Close-Out

Follow `.claude/skills/close-out.md`. Verify FLAGGED-blocks-stage-commit-push before staging.

Write close-out to `argus/docs/sprints/synthesis-2026-04-26/session-4-closeout.md`.

**Commit pattern:**
```bash
cd argus/workflow
git add protocols/operational-debrief.md bootstrap-index.md
git commit -m "synthesis-2026-04-26 S4: operational-debrief.md (NEW) + bootstrap routing"
git push origin main

cd ..
git add workflow docs/sprints/synthesis-2026-04-26/session-4-closeout.md
git commit -m "synthesis-2026-04-26 S4: advance workflow submodule + close-out report"
git push
```

## Tier 2 Review (Mandatory — @reviewer Subagent)

Standard invocation. Review writes to `argus/docs/sprints/synthesis-2026-04-26/session-4-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **F2 recurring-event-driven framing** — primary check this session. §1 has all 3 patterns clearly labeled with concrete examples for each.
2. **F3 execution-anchor-commit terminology** — "execution-anchor commit" is the primary term throughout §2; "boot commit" appears only as one example/legacy reference.
3. **3 non-trading examples in §3** — deployment retrospective + post-incident review + weekly health review. NOT trading-session debrief.
4. **§5 ARGUS reference is one example, not the universal pattern** — ARGUS-specific terminology ("DEF," "trading session") confined to §5; §§1–4 are project-agnostic.
5. **No safety-tag taxonomy** anywhere (B3 escalation if present).
6. **Cross-reference to campaign-orchestration.md §1** is present in the file's preamble.
7. **Bootstrap-index existing entries preserved** (R15).

## Sprint-Level Regression Checklist (for @reviewer)

See review-context.md §"Embedded Document 3." For Session 4: R7 (bootstrap routing for operational-debrief), R9 (workflow-version on new file), R11 (Origin footnote), R12 (F2/F3 — primary checks), R13 (no safety-tag), R15 (bootstrap existing entries), R20 (ARGUS runtime), R16 (close-out file).

## Sprint-Level Escalation Criteria (for @reviewer)

See review-context.md §"Embedded Document 4." For Session 4: B2 (bootstrap routing miss), B3 (safety-tag reintroduction — high-risk this session given the protocol covers the debrief topic that the rejected taxonomy was originally proposed for), B4 (F2/F3 not addressed), D3 (scope creep — operational-debrief.md must not address campaign-orchestration topics already in Session 3's output).
