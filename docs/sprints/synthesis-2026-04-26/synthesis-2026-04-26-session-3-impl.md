# Sprint synthesis-2026-04-26, Session 3: campaign-orchestration.md + impromptu-triage Extension + Bootstrap Routing

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** (Per the keystone Pre-Flight wiring landed in Session 1.)

2. **Verify Sessions 0, 1, 2 have landed:**
   ```bash
   # Session 0
   grep -c "^- \*\*P2[6789] candidate:\*\*" argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md
   # Must return 4

   # Session 1
   grep -c "Read .*\.claude/rules/universal\.md" argus/workflow/templates/implementation-prompt.md
   # Must return ≥ 1
   grep -c "^RULE-051:\|^RULE-052:\|^RULE-053:" argus/workflow/claude/rules/universal.md
   # Must return 3

   # Session 2
   grep -c "^**Synthesis status:**" argus/workflow/evolution-notes/2026-04-21-*.md | wc -l
   # Must return 3 (one match per file across 3 files)
   grep -c "## Hybrid Mode" argus/workflow/templates/work-journal-closeout.md
   # Must return ≥ 1
   ```
   If any check fails, **HALT and report** (escalation criterion D1).

3. Read these files to load context:
   - `argus/docs/sprints/synthesis-2026-04-26/review-context.md`
   - `argus/workflow/evolution-notes/2026-04-21-debrief-absorption.md` (the primary source for absorption/coordination-surface patterns; you'll be generalizing its content into the new protocol)
   - `argus/docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` (existing ARGUS campaign-close artifact; reference for the 7-point check + decision matrix patterns)
   - `argus/workflow/protocols/impromptu-triage.md` (current state; you'll be extending it)
   - `argus/workflow/bootstrap-index.md` (current state; you'll be adding 2 routing entries — one Conversation Type entry + one Protocol Index row)
   - `argus/workflow/protocols/sprint-planning.md` §"Phase A" (reference for protocol-style structure)

4. Verify clean working tree in both argus and workflow submodule.

## Objective

Land the first new protocol of the sprint plus its bootstrap-routing wiring plus the impromptu-triage two-session-scoping extension that depends on a Session 5 deliverable. After this session, the campaign-orchestration body of knowledge from Sprint 31.9 has a deterministic home in the metarepo.

This session is the largest single design-judgment session in the sprint. Structure it into 4 sub-phases and commit between sub-phases if context budget warrants — the file's structure is well-defined by this prompt, and each sub-phase is a natural checkpoint.

## Forward Dependency Notice

This session's **Sub-Phase 3** edits `protocols/impromptu-triage.md` to reference `templates/scoping-session-prompt.md` — a file that does NOT yet exist. It is created in Session 5.

This is **Pattern (a)** per the session-breakdown forward-dep handling: reference the path proactively with a note. Do NOT hold the impromptu-triage edit until Session 5; do NOT create the scoping-session-prompt template here (that's Session 5's job).

The reference looks correct ahead of file creation. Tier 2 review of this session acknowledges the forward-dep; Tier 2 review of Session 5 verifies the file now exists. The window between Session 3 and Session 5 has a "broken link" to scoping-session-prompt.md — operator-acknowledged.

## Requirements

### Sub-Phase 1: Create campaign-orchestration.md skeleton + main sections

Create the new file at `argus/workflow/protocols/campaign-orchestration.md`. The file is large (~250–350 lines expected). Structure:

```markdown
<!-- workflow-version: 1.0.0 -->
<!-- last-updated: 2026-04-26 -->

# Campaign Orchestration

A **campaign** is a multi-session work effort with persistent coordination state — typically 5+ sessions over multiple days, often with multiple parallel tracks, an accumulating findings/DEFs/judgment register, and a non-trivial close-out narrative. Campaigns differ from standard sprints in shape and require additional coordination machinery.

This protocol covers: campaign absorption (folding new mid-campaign work into ongoing tracks), supersession (when a later artifact replaces an earlier one), authoritative-record preservation (sealing campaign internals at close), cross-track close-out, pre-execution gates, naming conventions, DEBUNKED finding status, the absorption-vs-sequential decision matrix, and the two-session SPRINT-CLOSE option for campaigns whose close-out itself merits its own session pair.

For the recurring-event-driven knowledge-stream patterns (operational debriefs, post-incident reviews, periodic operational reviews) see `protocols/operational-debrief.md`. For the impromptu-vs-extend-current-sprint decision see `protocols/impromptu-triage.md`. For multi-stage execution DAGs see `templates/stage-flow.md`.

## When This Protocol Applies

Apply when a sprint or work effort has at least 2 of:
- 5+ sessions executed serially or in parallel.
- A persistent coordination surface (a Claude.ai conversation, an issue tracker with a campaign label, a wiki page with a running register — any persistent artifact tracking work-in-flight beyond a single session).
- Cross-session findings, DEFs, or judgment calls that accumulate (not just per-session deltas).
- A close-out that requires synthesizing across sessions (not just summarizing the last one).

Standard sprints (3–8 serial sessions, single coordination thread) use `protocols/sprint-planning.md` directly without this protocol's machinery.

## 1. Campaign Absorption

When new work surfaces mid-campaign — a new finding, an unexpected DEF closure opportunity, an in-flight scope addition — the campaign coordination surface decides whether to ABSORB the work into the ongoing campaign or DEFER it to a follow-on. The decision uses the absorption decision matrix (§8 below).

Absorption is judged along these axes (campaign-specific specifics vary; these are the typical dimensions):

- **Work-execution state.** Is the relevant track currently executing, between sessions, or post-close? Absorbing into a running session is high-risk; absorbing between sessions is low-risk; absorbing post-close requires reopening (high-cost).
- **Incoming-work size.** Is the new work a single small fix (1 session of effort), a feature (2–4 sessions), or a meaningful pivot (5+ sessions)? Larger work is biased toward DEFER.
- **Cross-track impact.** Does the new work affect tracks beyond the surfacing track? If yes, absorption requires cross-track coordination; bias toward DEFER unless coordination cost is tractable.
- **Operator-judgment availability.** Is the operator available within the absorption window? If not, defer.

When absorbing, the campaign coordination surface generates a brief absorption note (typically 1–2 paragraphs) and updates the running register. The new work joins the campaign's execution graph; downstream sessions reference the updated graph.

When deferring, the campaign coordination surface logs a DEFERRED entry in the running register with a clear trigger condition (e.g., "Next sprint touching X" or "Next strategic check-in").

<!-- Origin: synthesis-2026-04-26 evolution-note-2 (debrief-absorption).
     Generalized from ARGUS Sprint 31.9 campaign-close where mid-campaign
     findings (DEF-204 mechanism diagnostic, IMPROMPTU-04, etc.) were
     absorbed via this two-axis judgment + running-register update
     pattern. -->

## 2. Supersession Convention

When a later campaign-internal artifact replaces an earlier one — for example, a refined version of a CAMPAIGN-CLOSE-PLAN supersedes the original after a mid-campaign pivot — the new artifact is named with a SUPERSEDES-ANNOTATION at the top:

```
**SUPERSEDES:** CAMPAIGN-CLOSE-PLAN-v1.md (committed YYYY-MM-DD; replaced YYYY-MM-DD because <reason>).
```

The superseded artifact is NOT deleted. It remains in the campaign folder, with an `**SUPERSEDED-BY:**` annotation added at its top:

```
**SUPERSEDED-BY:** CAMPAIGN-CLOSE-PLAN-v2.md (committed YYYY-MM-DD; this version replaced because <reason>).
```

Both artifacts persist as authoritative-record. The supersession chain reads forward from any superseded artifact to its current replacement.

## 3. Authoritative-Record Preservation

At campaign close, the campaign folder contains:
- The campaign-close artifacts (CAMPAIGN-CLOSE-PLAN, RUNNING-REGISTER, CAMPAIGN-COMPLETENESS-TRACKER, etc.).
- Per-session close-outs and reviews.
- The campaign synthesis SUMMARY.md (the operator-facing one-pager).
- Any superseded prior versions (per §2).

This entire folder is then **sealed**. No subsequent commit modifies its contents. If a future sprint references campaign findings, it does so by reference (citing the campaign folder + relevant section), not by edit.

The sealing convention prevents post-hoc rewriting of campaign history. If a finding turns out to be wrong (per §7 DEBUNKED status), the correction lives in a NEW artifact, not as an edit to the original.

For RETRO-FOLD-style synthesis sprints that consume campaign artifacts, the consumed artifacts retain their byte-frozen state; the synthesis sprint produces NEW protocol/template content that cites the campaign artifacts as Origin evidence.

<!-- Origin: synthesis-2026-04-26 N1.6 (sealed campaign folders). ARGUS
     Sprint 31.9's campaign folder (`docs/sprints/sprint-31.9/`) is the
     reference instance of this pattern: 39 files, sealed at close,
     never edited subsequently. Synthesis sprints (this one) consume
     them as Origin references. -->

## 4. Cross-Track Close-Out

A multi-track campaign produces close-out artifacts per track AND a cross-track synthesis. The cross-track synthesis covers:

- Per-track outcomes (one line each).
- Cross-track findings (anything that surfaced in 2+ tracks).
- Cross-track recommendations (anything affecting future campaigns or sprints).
- Per-track deferrals (consolidated).

The cross-track synthesis is the campaign's primary handoff to the next planning conversation. Per-track close-outs serve as deeper reference but are not the primary input.

## 5. Pre-Execution Gate

Before any campaign session executes, the pre-execution gate verifies:

- [ ] All prior session close-outs are present in the campaign folder.
- [ ] All prior Tier 2 reviews are CLEAR or CONCERNS_RESOLVED (no open ESCALATE or unresolved CONCERNS).
- [ ] The running register is current (last update timestamp ≤ 24h old, or operator-judgment override).
- [ ] The session being initiated is the next in the execution graph (not skipping a dependency).
- [ ] If the session is parallel-tracked, the parallel track's coordination state has been read.

Failure on any item halts session execution until resolved. The gate is encoded in the session's implementation-prompt Pre-Flight section as explicit grep + ls + state-check commands.

## 6. Naming Conventions

Campaign-internal artifacts use prefix-style names that signal their role:

| Prefix | Meaning |
|---|---|
| `CAMPAIGN-CLOSE-PLAN.md` | The campaign-close planning artifact (one per campaign) |
| `CAMPAIGN-CLOSE-A-`, `CAMPAIGN-CLOSE-B-`, ... | Sequential close-out sessions during the campaign-close phase |
| `CAMPAIGN-COMPLETENESS-TRACKER.md` | Cross-session completeness checklist |
| `RUNNING-REGISTER.md` | Accumulating findings/DEFs/judgment register |
| `SPRINT-CLOSE-A-`, `SPRINT-CLOSE-B-`, ... | Sessions in the two-session SPRINT-CLOSE pattern (§9 below) |
| `IMPROMPTU-NN-` | Mid-campaign impromptu sessions (NN = sequential) |
| `FIX-NN-<kebab-name>` | A specific fix work-item; NN sequential within campaign |

The naming is a convention not a hard rule; campaigns adopt it for legibility. Departures should be conscious decisions, not drift.

## 7. DEBUNKED Finding Status

A finding initially recorded as a DEF or candidate may, on later investigation, turn out to be wrong (the symptom was misdiagnosed, the root cause was different, the original analysis used incorrect data). When this happens, the finding is marked DEBUNKED — not closed, not resolved, but explicitly invalidated.

DEBUNKED status differs from CLOSED:
- CLOSED: the issue was real and is now fixed.
- DEBUNKED: the issue was not real; the original analysis was wrong.

A DEBUNKED entry includes:
- The original finding text (preserved).
- A `**DEBUNKED:**` annotation with date, reason, and reference to the corrective analysis.
- A pointer to the new finding (if any) that the corrective analysis surfaced.

DEBUNKED status protects the audit trail. Without it, an operator scanning closed findings would not know that one of them was actually a misdiagnosis.

<!-- Origin: synthesis-2026-04-26 evolution-note-2 + ARGUS Sprint 31.9
     campaign-close where DEF-XXX (stale during campaign-close debugging)
     was identified as DEBUNKED rather than auto-closed. -->

## 8. Absorption-vs-Sequential Decision Matrix

For each candidate piece of new mid-campaign work, evaluate:

| Dimension | Bias toward ABSORB | Bias toward DEFER |
|---|---|---|
| Work size | ≤1 session | ≥2 sessions |
| Cross-track impact | Single track | Multi-track |
| Execution-state of relevant track | Between sessions | Mid-session |
| Operator availability | Available now | Unavailable in next 24h |
| Current campaign load | Light (1–2 active tracks) | Heavy (3+ active tracks) |
| Risk of context-window blow-up if absorbed | Low | Medium-to-high |
| Strategic urgency | Imminent (blocks downstream work) | Non-blocking |

Apply the matrix as judgment, not algorithm. If the dimensions point in conflicting directions, default to DEFER (lower-risk default). Document the decision in the running register either way.

## 9. Two-Session SPRINT-CLOSE Option

For campaigns where the close-out itself is non-trivial — multi-track synthesis, large doc-sync, formal handoff — the close-out runs as TWO sessions instead of folding into the final implementation session:

- **SPRINT-CLOSE-A.md:** First close-out session. Runs the §4 cross-track close-out narrative, drafts the campaign SUMMARY, drafts the doc-sync prompts, identifies any deferred items.
- **SPRINT-CLOSE-B.md:** Second close-out session. Lands the doc-sync, finalizes the SUMMARY, seals the campaign folder per §3.

The split is appropriate when SPRINT-CLOSE work would push the close-out session past compaction-risk limits (typically score ≥14 per `protocols/sprint-planning.md` Phase A). Standard sprints fold close-out into the final implementation session.

<!-- Origin: synthesis-2026-04-26 P33. ARGUS Sprint 31.9 ran
     SPRINT-CLOSE-A and SPRINT-CLOSE-B as a paired two-session structure
     because the close-out (cross-track synthesis + 12 between-session
     doc-syncs + final SUMMARY) would have blown a single session's
     context budget. -->

## 10. Appendix: 7-Point Check (Optional, Conditionally Applies)

[*This appendix applies only when the campaign coordination surface is a long-lived Claude.ai conversation that produces handoff prompts for Claude Code sessions. Other coordination surfaces (issue trackers, wikis) have their own native verification mechanisms and do not need this check. Skip the appendix if your coordination surface is not a long-lived Claude.ai conversation.*]

When a Claude.ai conversation operates as a campaign coordination surface — accumulating context across many sessions, generating multiple handoff prompts, tracking the running register — the conversation is at risk of compaction and silent context loss. The 7-point check verifies the conversation's state at planned checkpoints (typically before generating each session's handoff prompt):

1. **Session count.** Is the next session-to-handoff the expected sequential session? (Off-by-one would indicate skipped state.)
2. **Running register currency.** Does the conversation have the latest running register state in context? (Stale register → missed updates.)
3. **Cross-track state.** If the campaign has parallel tracks, is the conversation aware of all tracks' current state? (Track drift → coordination errors.)
4. **Open ESCALATE/CONCERNS resolution.** Are any prior sessions' Tier 2 reviews still open with unresolved findings? (Open findings → premature next session.)
5. **Recent commit alignment.** Does the conversation's understanding of `main` HEAD match the actual git state? (Drift → stale handoff.)
6. **Sprint-spec scope drift.** Has the campaign's actual work drifted from the sprint-spec scope? (Drift → re-scope needed before continuing.)
7. **Compaction self-check.** Is any of the above context degraded or contradictory? (Yes → halt and reload from authoritative artifacts.)

The 7-point check is a discipline, not a tool. The campaign coordination surface runs through it before generating each handoff prompt. Failure on any point halts handoff generation until resolved (typically by reloading from the running register and recent close-outs).

<!-- Origin: synthesis-2026-04-26 P32. ARGUS Sprint 31.9's campaign-tracking
     conversation ran a similar 7-point pattern manually before each
     session handoff. Codifying as appendix (rather than a standalone
     protocol) because the check is conditional on the coordination
     surface shape — only Claude.ai conversations need it. Other
     coordination surfaces (issue trackers, wikis) get their state from
     the native tooling rather than from accumulated conversation
     context. F10: conditional framing applied. -->

## Cross-References

- `protocols/operational-debrief.md` — recurring-event-driven knowledge streams (operational debriefs, post-incident reviews) that feed campaign absorption (§1).
- `protocols/impromptu-triage.md` — when to absorb mid-campaign vs. spawn impromptu sprint vs. defer.
- `protocols/sprint-planning.md` — protocol invoked by the campaign coordination surface for each session's planning.
- `templates/stage-flow.md` — DAG artifact template for multi-track campaign execution graphs.
- `templates/work-journal-closeout.md` §"Hybrid Mode" — non-standard-shape close-out structure for campaigns.
- `templates/doc-sync-automation-prompt.md` §"Between-Session Doc-Sync" — for campaign-internal find/replace patches.
- `claude/skills/close-out.md` — per-session close-out skill (used by every campaign session).
```

This is the full content of `protocols/campaign-orchestration.md`. Adjust prose as needed for fluency, but preserve all numbered sections (1–9 + appendix), all Origin footnotes, and all cross-references.

**Verification:**
```bash
ls argus/workflow/protocols/campaign-orchestration.md
# Expected: file exists

grep -c "^## [0-9]" argus/workflow/protocols/campaign-orchestration.md
# Expected: 9 (sections 1-9)

grep -c "^## Appendix\|## 10" argus/workflow/protocols/campaign-orchestration.md
# Expected: ≥ 1 (appendix)

grep -c "Origin: synthesis-2026-04-26" argus/workflow/protocols/campaign-orchestration.md
# Expected: ≥ 4 (one per substantive Origin-cited section)

grep -c "campaign coordination surface" argus/workflow/protocols/campaign-orchestration.md
# Expected: ≥ 3 (F1 generalized terminology consistently used)

grep -c "Work Journal conversation" argus/workflow/protocols/campaign-orchestration.md
# Expected: ≤ 2 (used only as one example of coordination-surface, not as universal pattern; per F1)

# F10 conditional framing
grep -B1 -A2 "appendix applies only when\|appendix only applies\|conditionally applies" argus/workflow/protocols/campaign-orchestration.md | head -5
# Expected: ≥ 1 match showing conditional-framing language
```

### Sub-Phase 2: Verify campaign-orchestration.md content quality

Before moving to Sub-Phase 3, run these content-quality checks on the just-created file:

1. **Origin footnote integrity:** every section that cites synthesis-2026-04-26 also cites either an evolution-note number, a P-number, or a specific ARGUS Sprint 31.9 artifact reference (CAMPAIGN-CLOSE-PLAN.md, etc.).
2. **F1 generalized-terminology coverage:** "campaign coordination surface" appears as the primary term; "Work Journal conversation" appears at most as one of multiple examples (issue tracker, wiki page).
3. **F6 generalized-axes coverage:** §1 absorption decision uses "work-execution state" + "incoming-work size" axes (not ARGUS-specific labels).
4. **F10 conditional-framing on appendix:** the §10 appendix begins with the explicit conditional framing italicized as shown.
5. **Cross-references resolve:** all the listed cross-references either point at files that already exist (sprint-planning.md, work-journal-closeout.md, doc-sync-automation-prompt.md, close-out.md, impromptu-triage.md) or files this sprint creates (operational-debrief.md → Session 4; stage-flow.md → Session 5).

If any check fails, fix in-session before moving to Sub-Phase 3.

### Sub-Phase 3: Extend impromptu-triage.md with two-session scoping variant

In `argus/workflow/protocols/impromptu-triage.md`:

Locate the existing structure (typically has sections like "When to use," "Decision criteria," "Scope," etc. — exact section names will vary by current state of the file). Add a new section titled "## Two-Session Scoping Variant" near the end of the file (before any closing cross-references, after the existing decision/scope sections).

Content:

```markdown
## Two-Session Scoping Variant

For impromptu work where the root cause is unclear and the fix requires investigation BEFORE a fix prompt can be generated, run a **two-session scoping pattern**:

- **Session 1 (Scoping):** A read-only investigation session producing structured findings + a generated fix prompt for Session 2. The session does NOT modify code; it produces dual artifacts (findings document + fix prompt). Uses `templates/scoping-session-prompt.md`. The findings document captures: code-path map, hypothesis verification, race conditions analyzed, root-cause statement, fix proposal, test strategy, risk assessment.
- **Session 2 (Fix):** The implementation session that consumes the fix prompt generated by Session 1. Standard implementation-prompt structure; the prompt is the Session 1 output verbatim (or with operator-edits applied between sessions).

When to use the two-session pattern:

- The symptom is reproducible but the root cause is non-obvious (e.g., "test fails intermittently in CI" where the cause could be a race condition, a non-deterministic timestamp, or a leaked test state).
- The candidate fix would touch ≥3 files or change a load-bearing module — high enough impact to warrant explicit scoping before commit.
- The investigator's confidence in the root cause is low (e.g., "I think it's X, but it could be Y or Z" — multiple hypotheses live).
- A previous quick-fix attempt failed and the recurring pattern needs deeper analysis.

When NOT to use the two-session pattern (use the standard single-session impromptu instead):

- Root cause is clear from symptoms (e.g., a typo in error-handling, an obvious off-by-one, a known regression pattern).
- Fix is bounded to a single file with clear behavioral change.
- Operator's prior experience with the system rules out alternatives.

The scoping session's findings document remains in the campaign folder as authoritative-record (per `protocols/campaign-orchestration.md` §3) even after the fix lands. Future investigations of similar symptoms can reference it.

> **Note:** `templates/scoping-session-prompt.md` is created in synthesis-2026-04-26 Session 5. If you encounter this section before that template exists, the path reference is correct ahead of file creation; create the template per Session 5's spec or wait for Session 5 to complete.

<!-- Origin: synthesis-2026-04-26 evolution-note-3 (phase-3-fix-generation-
     and-execution). ARGUS Sprint 31.9 ran several scoping-session +
     fix-session pairs (e.g., IMPROMPTU-04 mechanism diagnostic, then
     IMPROMPTU-05 fix). Generalizing into impromptu-triage as a
     standalone variant. -->
```

Bump impromptu-triage.md version header (e.g., 1.1.0 → 1.2.0).

**Verification:**
```bash
grep -c "## Two-Session Scoping Variant" argus/workflow/protocols/impromptu-triage.md
# Expected: ≥ 1
grep -c "templates/scoping-session-prompt\.md" argus/workflow/protocols/impromptu-triage.md
# Expected: ≥ 1 (the forward reference)
grep -c "Session 1 (Scoping)\|Session 2 (Fix)" argus/workflow/protocols/impromptu-triage.md
# Expected: ≥ 2
```

### Sub-Phase 4: Bootstrap-index routing entries

In `argus/workflow/bootstrap-index.md`:

Locate two sections:
1. The "Conversation Type → What to Read" section (or equivalent — look for a list/table mapping conversation types to protocols).
2. The "Protocol Index" table.

**Add a new "Conversation Type → What to Read" entry** in the appropriate location (alphabetical by conversation type, or wherever existing entries are organized):

```markdown
- **Campaign Orchestration / Absorption / Close** — read `protocols/campaign-orchestration.md` for the full protocol covering campaign absorption (§1), supersession (§2), authoritative-record preservation (§3), cross-track close-out (§4), pre-execution gates (§5), naming conventions (§6), DEBUNKED status (§7), absorption-vs-sequential decision matrix (§8), and the two-session SPRINT-CLOSE option (§9). Also read `protocols/sprint-planning.md` for per-session planning within the campaign.
```

**Add a new Protocol Index row:**

```markdown
| `protocols/campaign-orchestration.md` | Multi-session campaigns with persistent coordination state (5+ sessions, multi-track, accumulating registers). | 1.0.0 |
```

Verify the bootstrap-index.md table format matches existing rows (column count, separator alignment).

**Verification:**
```bash
grep -c "Campaign Orchestration" argus/workflow/bootstrap-index.md
# Expected: ≥ 1 (in Conversation Type section)

grep -c "campaign-orchestration\.md" argus/workflow/bootstrap-index.md
# Expected: ≥ 1 (in Protocol Index)

# Verify existing entries unchanged
git diff HEAD argus/workflow/bootstrap-index.md | grep "^<" | grep -v "^---"
# Expected: empty (no deletions; only additions)
```

## Constraints

- **Do NOT modify** any path under `argus/argus/`, `argus/tests/`, `argus/config/`, `argus/scripts/`. Triggers escalation criterion A1.
- **Do NOT modify** Sessions 0/1/2 outputs (universal.md, close-out.md, the 4 templates, scaffold/CLAUDE.md, evolution-notes/README.md, the 3 evolution notes, SPRINT-31.9-SUMMARY.md). They are stable.
- **Do NOT create** `templates/scoping-session-prompt.md` in this session — it's Session 5's job. Pattern (a) forward-dep applies.
- **Do NOT create** `protocols/operational-debrief.md` in this session — it's Session 4's job (cross-references from campaign-orchestration are forward-references; operational-debrief.md will exist when Session 4 lands).
- **Do NOT modify** files outside the explicit list (campaign-orchestration.md created; impromptu-triage.md modified; bootstrap-index.md modified). Any other modification triggers scope-creep escalation per D3.
- **Do NOT enumerate** specific RULEs in `campaign-orchestration.md` — the keystone wiring propagates universal RULEs without per-protocol enumeration.
- **Do NOT use** safety-tag taxonomy (4-tag flat or core+modifier) anywhere in `campaign-orchestration.md`. The pattern is rejected; reintroduction triggers escalation criterion B3. The rejected-pattern addendum lands in Session 6 (codebase-health-audit.md), not this protocol.
- **Do NOT use** ARGUS-specific terminology ("DEF" universally, "trading session" universally) without contextual framing. Generalized terminology per F1, F6, F10. Triggers escalation criterion B4 if Session 6 close-out's F1–F10 mapping cannot point at this session.

## Test Targets

No executable code, no tests. Verification is grep-based per sub-phase.

## Definition of Done

- [ ] Sub-Phase 1: `protocols/campaign-orchestration.md` exists; workflow-version 1.0.0; 9 numbered sections + appendix; all Origin footnotes present; cross-references list complete
- [ ] Sub-Phase 2: F1 + F6 + F10 generalized-terminology checks pass (grep counts above)
- [ ] Sub-Phase 3: `protocols/impromptu-triage.md` has Two-Session Scoping Variant section; references `templates/scoping-session-prompt.md` (forward-dep noted in section text); version bumped
- [ ] Sub-Phase 4: `bootstrap-index.md` has new Conversation Type entry + Protocol Index row; existing entries unchanged
- [ ] All verification grep + diff commands run; outputs captured in close-out
- [ ] No scope creep beyond the explicit file list
- [ ] Close-out report written to `argus/docs/sprints/synthesis-2026-04-26/session-3-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Sessions 0/1/2 outputs untouched | `git diff HEAD --name-only -- argus/workflow/claude/ argus/workflow/templates/work-journal-closeout.md argus/workflow/templates/doc-sync-automation-prompt.md argus/workflow/templates/implementation-prompt.md argus/workflow/templates/review-prompt.md argus/workflow/scaffold/ argus/workflow/evolution-notes/` returns empty |
| ARGUS runtime untouched | `git diff HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/` returns empty |
| Bootstrap-index existing entries preserved | `git diff HEAD argus/workflow/bootstrap-index.md \| grep "^<"` returns empty |
| F1 generalized terminology | `grep "campaign coordination surface" argus/workflow/protocols/campaign-orchestration.md \| wc -l` ≥ 3 |
| F6 generalized axes | §1 of campaign-orchestration.md uses "work-execution state" + "incoming-work size" axes (not "trading state" / etc.) |
| F10 conditional-framing on appendix | `grep -B1 -A2 "appendix applies only when" argus/workflow/protocols/campaign-orchestration.md` returns the conditional-framing block |
| No safety-tag taxonomy | `grep -E "(safe-during-trading\|weekend-only\|read-only-no-fix-needed\|deferred-to-defs)" argus/workflow/protocols/campaign-orchestration.md` returns empty |
| Forward-dep on scoping-session-prompt.md flagged | The Two-Session Scoping Variant section explicitly notes the file is created in Session 5 |
| Workflow-version on new file | `head -3 argus/workflow/protocols/campaign-orchestration.md` shows `<!-- workflow-version: 1.0.0 -->` |

## Close-Out

Follow `.claude/skills/close-out.md`. Verify FLAGGED-blocks-stage-commit-push (from Session 1's strengthening) before staging.

Write close-out to `argus/docs/sprints/synthesis-2026-04-26/session-3-closeout.md`.

**Commit pattern:**
```bash
cd argus/workflow
git add protocols/campaign-orchestration.md protocols/impromptu-triage.md bootstrap-index.md
git commit -m "synthesis-2026-04-26 S3: campaign-orchestration.md (NEW) + impromptu-triage two-session scoping + bootstrap routing"
git push origin main

cd ..
git add workflow docs/sprints/synthesis-2026-04-26/session-3-closeout.md
git commit -m "synthesis-2026-04-26 S3: advance workflow submodule + close-out report"
git push
```

Wait for green CI; record URL.

## Tier 2 Review (Mandatory — @reviewer Subagent)

Invoke @reviewer with:
1. Review context: `argus/docs/sprints/synthesis-2026-04-26/review-context.md`
2. Close-out: `argus/docs/sprints/synthesis-2026-04-26/session-3-closeout.md`
3. Diff range: metarepo + argus
4. Files NOT to have been modified: anything outside the 3 listed (campaign-orchestration.md created; impromptu-triage.md + bootstrap-index.md modified)

@reviewer writes review to `argus/docs/sprints/synthesis-2026-04-26/session-3-review.md`.

## Post-Review Fix Documentation

Standard post-review-fix loop if CONCERNS reported.

## Session-Specific Review Focus (for @reviewer)

1. **Forward-dep on scoping-session-prompt.md** — Verify Sub-Phase 3 explicitly notes the file is created in Session 5. Pattern (a) approval is operator-acknowledged, but the dead-link window (Sessions 3 → 5) must be flagged in the protocol text itself.
2. **F1 generalized terminology** in campaign-orchestration.md — primary term is "campaign coordination surface"; "Work Journal conversation" appears only as one example (≤2 occurrences, contextually framed).
3. **F6 generalized absorption axes** in §1 — "work-execution state" + "incoming-work size" + others; not ARGUS-specific labels.
4. **F10 conditional framing** on the §10 appendix — explicit "appendix applies only when..." language.
5. **No safety-tag taxonomy** anywhere in the new protocol (B3 escalation if present).
6. **Origin footnotes** on every substantive new section (≥4 across the new protocol).
7. **Cross-references** point at files that either exist now or are created in subsequent sessions of this sprint (operational-debrief.md → Session 4; stage-flow.md → Session 5; scoping-session-prompt.md → Session 5).
8. **Bootstrap-index existing entries unchanged** (R15 invariant — additions only, no edits).

## Sprint-Level Regression Checklist (for @reviewer)

See review-context.md §"Embedded Document 3." For Session 3: R6 (keystone wiring still in place — verify Session 1 outputs untouched), R7 (bootstrap routing entry for campaign-orchestration), R9 (new file workflow-version header), R11 (Origin footnotes), R12 (F1, F6, F10 — partial coverage; full coverage requires Session 6), R13 (no safety-tag taxonomy reintroduction), R15 (bootstrap-index existing entries preserved), R20 (ARGUS runtime), R16 (close-out file).

## Sprint-Level Escalation Criteria (for @reviewer)

See review-context.md §"Embedded Document 4." For Session 3: B2 (bootstrap routing miss — primary risk), B3 (safety-tag reintroduction), B4 (F1/F6/F10 not addressed — partial; full check at Session 6), C4 (forward-dep handling — verify the Pattern (a) note is present in the impromptu-triage.md extension), D3 (scope creep — campaign-orchestration.md must not address Session 4/5/6 scope).
