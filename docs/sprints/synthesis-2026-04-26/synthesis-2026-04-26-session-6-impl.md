# Sprint synthesis-2026-04-26, Session 6: codebase-health-audit.md Major Expansion + sprint-planning.md Cross-Reference

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.**

2. **Verify Sessions 0–5 have landed:**
   ```bash
   # Sessions 0–4 (abbreviated)
   grep -c "^- \*\*P2[6789] candidate:\*\*" argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md  # 4
   grep -c "^RULE-051:\|^RULE-052:\|^RULE-053:" argus/workflow/claude/rules/universal.md  # 3
   grep -c "^**Synthesis status:**" argus/workflow/evolution-notes/2026-04-21-*.md | wc -l  # 3
   ls argus/workflow/protocols/campaign-orchestration.md  # exists
   ls argus/workflow/protocols/operational-debrief.md  # exists

   # Session 5
   ls argus/workflow/templates/stage-flow.md  # exists
   ls argus/workflow/templates/scoping-session-prompt.md  # exists
   ls argus/workflow/scripts/phase-2-validate.py  # exists
   ```
   If any check fails, **HALT and report**.

3. Read these files to load context (this is the heaviest pre-flight in the sprint):
   - `argus/docs/sprints/synthesis-2026-04-26/review-context.md` (full sprint contract)
   - `argus/workflow/protocols/codebase-health-audit.md` (the file you're expanding from 1.0.0 to 2.0.0; current state ~87 lines, target ~400–500 lines)
   - `argus/workflow/evolution-notes/2026-04-21-argus-audit-execution.md` (primary source for Phase 1 + Phase 2 patterns)
   - `argus/workflow/evolution-notes/2026-04-21-phase-3-fix-generation-and-execution.md` (primary source for Phase 3 patterns)
   - `argus/docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` (ARGUS-specific; reference for the overrides table + scale-tiered tooling structure)
   - `argus/workflow/protocols/sprint-planning.md` (you'll be adding 1 cross-reference line)
   - `argus/workflow/protocols/campaign-orchestration.md` (Session 3's output; cross-referenced from the audit expansion)
   - `argus/workflow/protocols/operational-debrief.md` (Session 4's output; cross-referenced)
   - `argus/workflow/templates/stage-flow.md` (Session 5's output; cross-referenced)
   - `argus/workflow/templates/scoping-session-prompt.md` (Session 5's output; cross-referenced)
   - `argus/workflow/scripts/phase-2-validate.py` (Session 5's output; the non-bypassable gate referenced from Phase 2)

4. Verify clean working tree.

## Objective

Land the largest single content expansion in the sprint: the codebase-health-audit protocol's major expansion from a Phase-1-only ~87-line file to a full Phase 1/2/3 ~400–500-line protocol. The expansion folds in all dispositions from evolution-note-1 (audit-execution) and evolution-note-3 (phase-3-fix-generation-and-execution), incorporates F1/F4/F5/F8/F9 generalized terminology, lands the rejected-safety-tag-taxonomy addendum, encodes the `phase-2-validate.py` non-bypassable gate, and integrates all prior sessions' new protocols/templates by cross-reference.

The file's workflow-version bumps to 2.0.0 (major) because Phase 2 + Phase 3 are entirely new content; this is a structural expansion, not a minor revision.

This session is the integration session — every prior session's output gets cited or cross-referenced from the audit expansion.

## Requirements

This session is structured into 4 sub-phases by audit Phase. Commit between sub-phases if context budget warrants. The file structure is well-defined; each sub-phase is a natural checkpoint.

### Sub-Phase 1: Phase 1 expansion

In `argus/workflow/protocols/codebase-health-audit.md`:

Bump version header:
- `<!-- workflow-version: 1.0.0 -->` → `<!-- workflow-version: 2.0.0 -->`
- `<!-- last-updated: ... -->` → `<!-- last-updated: 2026-04-26 -->`

The file currently has Phase 1 content but is incomplete. Restructure to have explicit `## Phase 1:`, `## Phase 2:`, `## Phase 3:` top-level sections. Phase 1 expands as follows (preserve any existing Phase 1 substantive content; add structure + the new sub-sections):

```markdown
## Phase 1: Scoping and Pre-Flight

Phase 1 frames the audit's scope, identifies coverage targets, and budgets sessions. The phase produces three artifacts: the closed-item health spot-check, the custom-structure rule decision, and the session-count budget.

### 1.1 Closed-Item Health Spot-Check

[F8 generalized terminology: this section uses "closed-item" not "DEF" — DEFs are an ARGUS-specific naming convention. The pattern applies to any tracker's closed items: GitHub Issues with "closed" status, Linear issues marked Done, Jira tickets in Resolved status, etc.]

Before scoping the audit, sample-check 5–10 recently-closed items from the project's tracker. For each:

- **Are they actually closed-and-fixed**, or closed-and-paper-over (CLOSED status set without verification)?
- **Did the close-action commit reference them** (e.g., commit message mentions issue ID)?
- **Are tests (if applicable) added or updated** as part of the close-action?
- **Is the closing rationale documented** somewhere durable (commit body, ticket comment, runbook)?

The spot-check produces a "closed-item hygiene" judgment: HEALTHY (≥80% are closed-and-fixed-and-traceable), DRIFTING (50–80%), or BROKEN (<50%). DRIFTING/BROKEN findings extend the audit's Phase 2 to include closed-item-hygiene reviews; HEALTHY findings allow the audit to proceed without that extension.

### 1.2 Custom-Structure Rule

The audit's structure (which phases run, which artifacts get produced, which validation gates apply) defaults to the structure documented in this protocol. The operator MAY customize when the project's specific shape warrants it (e.g., a security-focused audit might prepend a Phase 0 threat-model review; a compliance audit might add a Phase 4 documentation completeness review).

Customizations MUST:
- Be documented in the audit's kickoff prompt with explicit rationale.
- Identify which deviations from default structure are operative.
- Re-validate that any default-structure validation gates are either preserved or replaced by equivalent custom gates.

### 1.3 Session-Count Budget

Estimate total sessions for the audit using the compaction-risk formula in `protocols/sprint-planning.md` Phase A. For audits, expect:

- Phase 1: 1 session (this scoping work).
- Phase 2: 2–6 sessions (depending on universe scope; multi-track audits run Phase 2 in parallel).
- Phase 3: 1–4 sessions (one per fix-group cluster identified in Phase 2).

A typical small-codebase audit lands at 4–6 total sessions; a mid-size codebase audit lands at 8–12; a large multi-module audit can exceed 15. If session-count budget exceeds 10, the audit is a campaign — apply `protocols/campaign-orchestration.md` for the coordination machinery.

<!-- Origin: synthesis-2026-04-26 evolution-note-1 (audit-execution) §S1
     dispositions S1.1, S1.2, S1.3. F8 generalized terminology applied
     to S1.1: "closed-item" replaces ARGUS-specific "DEF". -->
```

**Verification (Sub-Phase 1):**
```bash
grep -c "^## Phase 1:\|^### 1\.[123]" argus/workflow/protocols/codebase-health-audit.md
# Expected: ≥ 4 (Phase 1 heading + 3 sub-sections)

grep -c "closed-item" argus/workflow/protocols/codebase-health-audit.md
# Expected: ≥ 2 (F8 generalized terminology)

# Check version bump applied
head -3 argus/workflow/protocols/codebase-health-audit.md | grep "workflow-version: 2.0.0"
# Expected: 1 match
```

### Sub-Phase 2: Phase 2 expansion

After Phase 1, append Phase 2:

```markdown
## Phase 2: Findings Generation

Phase 2 produces the audit's findings CSV — a row-per-finding structured artifact that Phase 3 consumes. Phase 2 also identifies hot files, sets per-finding decisions (fix-now / fix-later / defer / debunk / scope-extend), and validates CSV integrity.

### 2.1 CSV Integrity + Override Table

The findings CSV uses the column schema documented in `scripts/phase-2-validate.py`'s module docstring. The schema's columns are: finding_id, file_path, issue_summary, mechanism_signature, decision, fix_session_id, rationale.

Override table: when a finding's decision needs to deviate from a default rule (e.g., a finding marked fix-later by the default policy but the operator decides fix-now because of cross-track impact), the override is documented in a separate `phase-2-overrides.md` artifact with: finding_id, default-decision, override-decision, rationale, operator-attribution. The override artifact lives alongside the CSV in the audit folder.

### 2.2 Scale-Tiered Tooling

The Phase 2 tooling (how findings are generated, who runs the queries, how aggregated) tiers by scope:

| Scale | Tooling |
|---|---|
| ≤500 LOC scoped | Manual review against checklist |
| 500–5K LOC scoped | Manual review + grep-driven discovery |
| 5K–50K LOC scoped | Grep-driven discovery + light static-analysis tools (linter rules, type-check baselines) |
| 50K–500K LOC scoped | Static-analysis tooling + scoped human review (focus on hot files) |
| >500K LOC scoped | Multi-track parallel audits per `protocols/campaign-orchestration.md`, each on a sub-universe |

Tier choice is operator-judgment; the scale boundary is a prompt, not a hard threshold.

### 2.3 Operator-Judgment Commit Pattern

When Phase 2 generates a finding that requires operator judgment to triage (e.g., "this looks like a candidate fix but it could also be intentional design"), the finding is committed to the CSV with `decision=fix-later` and the operator's judgment is captured in the rationale column (e.g., "needs operator triage: is this intentional?"). The Phase 3 fix-group clustering picks these up; if the operator's eventual decision is "intentional," the finding gets re-labeled `decision=debunk` per §2.6 below.

This pattern preserves the finding in the audit trail (so it's not lost) without forcing premature decisions.

### 2.4 Approval-Heavy Pattern with Hot-File Carve-Out

For high-risk codebase regions, Phase 2 may set `decision=fix-now` only with operator explicit approval per finding (rather than per fix-group). This "approval-heavy" pattern is the default for hot files (§2.7 below). The carve-out: if a hot-file finding is below a triviality threshold (e.g., a single-line typo fix, a clearly-cosmetic refactor), the per-finding approval may be skipped and approval batched at the fix-group level.

### 2.5 Combined Doc-Sync

Phase 2 may discover doc-sync work (CLAUDE.md drift, runbook staleness) as a side effect of finding generation. Such findings get `decision=fix-now` and a fix_session_id pointing at a combined doc-sync session that runs alongside Phase 3 fix sessions. This avoids fragmenting doc-sync across many small fix-now sessions.

### 2.6 In-Flight Triage Amendment

Phase 2 findings can change classification mid-audit when new information arrives. The amendment pattern: finding_id stays stable; the row's decision column updates; the rationale column appends the amendment ("Amended YYYY-MM-DD: was fix-later, now fix-now because..."). The audit's `phase-2-overrides.md` artifact tracks all amendments. DEBUNKED status (per `protocols/campaign-orchestration.md` §7) is the most common amendment direction.

### 2.7 Hot Files Operationalizations

[F4 tiered operationalizations: "hot files" is the abstract concept; the operationalization tier varies by project shape. Adopt one tier; do not adopt all.]

Operationalize "hot files" using ONE of the following project-shape-appropriate tiers:

1. **Recent-bug count.** Files with ≥3 closed bugs in the last 90 days are hot.
2. **Recent-churn.** Files with ≥10 commits in the last 30 days are hot.
3. **Post-incident subjects.** Files identified as root-cause in the last 6 months of post-incident reviews are hot.
4. **Maintained list.** A project-maintained `hot-files.md` document (operator-curated, updated quarterly) lists hot files explicitly.
5. **Code-ownership signal.** Files with high committer-diversity (≥5 distinct committers in the last 90 days) are hot, indicating shared-stewardship complexity.

Hot files trigger the approval-heavy pattern (§2.4) by default. The choice of tier is project-specific; document the choice in the audit kickoff.

### 2.8 phase-2-validate.py Non-Bypassable Gate

**Phase 2 cannot complete until `scripts/phase-2-validate.py` exits zero against the findings CSV.** The validator runs 6 checks (row column-count / decision-value canonical / fix-now has fix_session_id / FIX-NN-kebab format / finding_id integrity / mechanism_signature for fix-now/fix-later). Before proceeding to Phase 3, the operator MUST:

1. Run `python3 scripts/phase-2-validate.py path/to/findings.csv`.
2. Confirm exit code is 0.
3. Capture the validator's PASS output in the audit close-out.

A non-zero exit halts Phase 3 generation. Fix the CSV (or fix the validator if the validator is buggy) and re-run before proceeding.

The validator does NOT validate safety tags. See §2.9 below.

### 2.9 Anti-pattern (do not reinvent)

[Important — this section documents a structural rejection. Future audits MUST NOT reintroduce the pattern below.]

A previous synthesis effort considered codifying a 4-tag safety taxonomy on Phase 2 findings (`safe-during-trading`, `weekend-only`, `read-only-no-fix-needed`, `deferred-to-defs`) or a core+modifier expansion thereof. **The taxonomy was empirically overruled** during ARGUS Sprint 31.9 execution — the operator ran fixes during active operational sessions regardless of tag, and the actual audit-trail mechanism turned out to be execution-anchor-commit correlation (per `protocols/operational-debrief.md` §2), not safety tags as routing.

**Do not reinvent this taxonomy.** If a future audit's findings need scheduling or routing logic, use:
- `decision` column values (canonical: fix-now, fix-later, defer, debunk, scope-extend) for fix-vs-defer.
- Fix-group cardinality (§3.7 below) for batching decisions.
- Operator-judgment-commit pattern (§2.3 above) for ambiguous findings.
- Execution-anchor-commit correlation (per `protocols/operational-debrief.md` §2) for audit-trail correlation.

The 4-tag safety taxonomy adds taxonomy-maintenance overhead without earned load-bearing role. Origin: synthesis-2026-04-26 Phase A pushback round 2 (operator empirically rejected the taxonomy based on Sprint 31.9 execution evidence).

<!-- Origin: synthesis-2026-04-26 evolution-note-1 (audit-execution) §S2
     dispositions S2.1–S2.7; Phase A pushback round 2 (safety-tag
     rejection); F4 tiered hot-files; F8 generalized terminology. -->
```

**Verification (Sub-Phase 2):**
```bash
grep -c "^## Phase 2:\|^### 2\.[1-9]" argus/workflow/protocols/codebase-health-audit.md
# Expected: ≥ 10 (Phase 2 heading + 9 sub-sections)

grep -c "phase-2-validate\.py" argus/workflow/protocols/codebase-health-audit.md
# Expected: ≥ 2 (referenced in §2.1 and gate enforced in §2.8)

# Imperative gate phrasing (escalation criterion C2)
grep -B2 -A2 "phase-2-validate\.py" argus/workflow/protocols/codebase-health-audit.md | grep -E "(cannot complete\|MUST\|before proceeding)" | head -3
# Expected: ≥ 1 match (imperative gate language present)

# Tiered hot-files (F4)
grep -E "(recent-bug\|recent-churn\|post-incident\|maintained list\|code-ownership)" argus/workflow/protocols/codebase-health-audit.md
# Expected: ≥ 5 (the 5 tiers in §2.7)

# Anti-pattern addendum present
grep -c "Anti-pattern\|do not reinvent" argus/workflow/protocols/codebase-health-audit.md
# Expected: ≥ 2

# Safety-tag terms present ONLY in the addendum context
grep -c "safe-during-trading\|weekend-only\|read-only-no-fix-needed\|deferred-to-defs" argus/workflow/protocols/codebase-health-audit.md
# Expected: ≥ 4 (the 4 tags listed in §2.9 only) — verify they appear with rejection-framing context
```

### Sub-Phase 3: Phase 3 expansion

After Phase 2, append Phase 3:

```markdown
## Phase 3: Fix Generation and Execution

Phase 3 takes Phase 2's validated findings CSV and produces fix prompts, schedules fix sessions, and tracks execution. The phase output is fix-session implementation prompts (one per fix-group cluster) plus the audit's overall close-out.

### 3.1 File-Overlap-Only DAG Scheduling

Fix sessions are scheduled into a DAG where the only dependency relation is **file overlap** — two fix sessions cannot run in parallel if they modify the same file. Other potential scheduling considerations (operator availability, CI capacity, deployment windows) are operator-judgment overlays on top of the file-overlap DAG, not dependency relations.

The file-overlap DAG is mechanically derivable: list each fix session's modified-files set; any two sessions with non-empty intersection are serialized; otherwise parallelizable.

This replaces an earlier proposed scheduling approach that combined file-overlap with a "safety-tag matrix" — see §2.9 (Anti-pattern). File-overlap alone is sufficient for scheduling; the matrix component was rejected.

### 3.2 sort_findings_by_file

Within Phase 3, findings are clustered into fix-groups by source file. A fix-group is a set of findings that all modify the same file or a tightly-coupled set of files (e.g., a class and its tests). This clustering reduces context-loading overhead per fix session: the implementer reads the file once, addresses all findings against it, commits.

The clustering is mechanical (sort findings by file_path; cluster contiguous same-file findings; cross-file fix-groups require explicit operator override). Document the clustering decision in the audit close-out.

### 3.3 Fingerprint-Before-Behavior-Change

[F5 expanded: 3 non-trading examples to ground the abstract pattern.]

Before a fix-group session changes behavior, the session establishes a **mechanism signature** (a fingerprint) for the bug being fixed. The signature is what's used to validate that the fix actually addresses the bug, not just suppresses the symptom.

The signature is captured in the Phase 2 CSV's `mechanism_signature` column (per `scripts/phase-2-validate.py` check 6). The fix session's test strategy validates against the signature.

**Three non-trading examples:**

#### 3.3.1 Pricing Engine Example

A pricing engine occasionally outputs a price 100× the correct value. The mechanism signature is "output > 50× input baseline AND occurs on first call after engine restart." The fix-session validates that post-fix, the signature is no longer reproducible (cold-start tests run; output stays within ≤2× baseline). Without a signature, a fix that "appears to work" might just have shifted the failure mode.

#### 3.3.2 A/B Test Cohort Example

An A/B test framework reports inconsistent cohort assignments — users sometimes flip cohorts within a session. The mechanism signature is "cohort_id changes within a single user session AND change correlates with backend instance routing." The fix-session validates that post-fix, cohort_id is stable across N=10000 user-session-simulations regardless of routing. Without a signature, the fix might pass cursory testing but still flip cohorts under specific routing patterns.

#### 3.3.3 ML Model Recommendation Example

A recommendation model occasionally recommends already-purchased items to users who have purchase-history. The mechanism signature is "recommended item_id appears in user's purchase_history within last 30 days, AND model version is v3.X." The fix-session validates that post-fix, the signature occurrence rate falls below 0.1% (matching the pre-bug baseline). Without a signature, "fixing" the model might just mask the issue while the underlying purchase-history-blindness persists.

### 3.4 Coordination-Surface Branch (Multi-Track Audits)

[F1: "campaign coordination surface" generalized terminology.]

For audits with multiple parallel Phase 3 tracks, the campaign coordination surface (per `protocols/campaign-orchestration.md`) tracks per-track progress. The surface is typically a Claude.ai conversation, but can be an issue tracker with a campaign label, a wiki page, or any persistent artifact tracking work-in-flight beyond a single session. Per-track close-outs feed into the audit's cross-track synthesis (per `protocols/campaign-orchestration.md` §4).

### 3.5 Scope-Extension Home

When a Phase 3 fix session discovers a new finding NOT in the original Phase 2 CSV, the finding gets added to a `phase-2-overrides.md` (per §2.6 in-flight triage amendment) with `decision=scope-extend`. Scope-extend findings are NOT addressed within the current fix-group session; they're either deferred to a follow-on fix session, queued for a future audit, or absorbed per `protocols/campaign-orchestration.md` §1 (Campaign Absorption) if the audit is operating as a campaign.

The scope-extension home prevents fix sessions from drifting into open-ended scope creep.

### 3.6 Contiguous Numbering

Fix sessions are numbered FIX-NN-<kebab-name> where NN is a contiguous integer sequence per audit. Skip-numbers indicate dropped sessions; the close-out documents reasons. Re-using a number indicates a re-run; the original session's artifacts are preserved with an explicit re-run annotation.

### 3.7 Fix-Group Cardinality

A fix-group is a set of findings sharing fix-session ownership. Cardinality guidance:

- **1–3 findings/group:** typical; one session per group is right-sized.
- **4–8 findings/group:** acceptable; session may need to split mid-execution if context-budget pressure surfaces.
- **9+ findings/group:** flag for re-clustering before fix-session generation; the group is too large for reliable single-session execution.

The cardinality is a heuristic, not a hard rule. Operator-judgment override is acceptable with rationale.

### 3.8 git-commit-body-as-state-oracle (OPTIONAL)

[F9: caveats on squash-merge.]

A useful pattern (when applicable): Phase 3 fix sessions write structured information into commit message bodies (closed-item references, mechanism-signature-validation results, coordination-surface state-update markers). Tools that scan commit bodies can derive audit state from git history without separate state files.

**Caveat:** this pattern is optional and brittle in environments with squash-merge or rebase-merge workflows. If the project uses GitHub PR squash-merge, individual fix-session commits collapse into a single squash commit and structured commit-body data is lost. Workarounds: include the structured data in the PR body (which survives squash) instead of individual commit bodies; or use a separate state file (e.g., `audit-state.jsonl`) maintained alongside the audit artifacts.

Use this pattern only if the project's git workflow preserves individual commits in the long-term branch (no squash, no rebase-flatten).

### 3.9 Cross-References

Phase 3 cross-references:
- `protocols/campaign-orchestration.md` — for multi-track audit coordination (§3.4).
- `protocols/operational-debrief.md` — for execution-anchor-commit correlation pattern (replaces rejected safety-tag taxonomy; see §2.9).
- `protocols/impromptu-triage.md` — when Phase 3 fix sessions surface unrelated impromptu work.
- `templates/stage-flow.md` — for documenting multi-track Phase 3 DAGs.
- `templates/scoping-session-prompt.md` — when a Phase 3 finding's root cause is non-obvious and needs a scoping session before the fix session.

<!-- Origin: synthesis-2026-04-26 evolution-note-3 (phase-3-fix-generation-
     and-execution) §S3 dispositions S3.1–S3.8 (excluding rejected
     N3.3 action-type routing and ID3.3 safety-tag session resolution).
     F1 generalized terminology; F5 3 non-trading examples (pricing
     engine, A/B test, ML model); F9 squash-merge caveat. -->
```

**Verification (Sub-Phase 3):**
```bash
grep -c "^## Phase 3:\|^### 3\.[1-9]" argus/workflow/protocols/codebase-health-audit.md
# Expected: ≥ 10 (Phase 3 heading + 9 sub-sections; some have nested 3.3.1/3.3.2/3.3.3)

# F5 3 non-trading examples
grep -c "Pricing Engine Example\|A/B Test Cohort Example\|ML Model Recommendation Example" argus/workflow/protocols/codebase-health-audit.md
# Expected: 3

# Verify no trading-specific examples leak in
grep -c "trading session\|market open\|tick\|paper trading" argus/workflow/protocols/codebase-health-audit.md
# Expected: 0 (or only in §2.9 anti-pattern context if any reference is needed there)

# F9 squash-merge caveat
grep -c "squash" argus/workflow/protocols/codebase-health-audit.md
# Expected: ≥ 1
```

### Sub-Phase 4: sprint-planning.md cross-reference + final F1–F10 verification

In `argus/workflow/protocols/sprint-planning.md`:

Locate an appropriate location (typically near the top of the file, in the "When to use this protocol" section, or in a "Related Protocols" section if one exists). Add a one-line cross-reference:

```markdown
For multi-session campaigns with persistent coordination state (5+ sessions, multi-track, accumulating registers), see `protocols/campaign-orchestration.md` for the coordination machinery layered on top of per-session sprint planning.
```

Bump sprint-planning.md's version header (minor bump, e.g., 1.X.Y → 1.(X+1).0 or 1.X.(Y+1) depending on existing convention).

**Final F1–F10 verification pass.** This is the audit's last opportunity to verify all 10 findings from the synthetic-stakeholder pass have been addressed somewhere in the sprint's outputs. Run these checks across the entire metarepo (not just this session's edits):

```bash
# F1: campaign coordination surface
grep -rh "campaign coordination surface" argus/workflow/protocols/ argus/workflow/templates/ | wc -l
# Expected: ≥ 4 (in campaign-orchestration.md, work-journal-closeout.md Hybrid Mode, codebase-health-audit.md §3.4)

# F2: recurring-event-driven framing
grep -rh "periodic.*operational debrief\|event-driven.*debrief\|periodic.*without.*cycle" argus/workflow/protocols/operational-debrief.md
# Expected: matches in §1.1, §1.2, §1.3

# F3: execution-anchor commit
grep -rh "execution-anchor commit" argus/workflow/protocols/operational-debrief.md | wc -l
# Expected: ≥ 4

# F4: tiered hot-files
grep -rh "recent-bug\|recent-churn\|post-incident.*subject\|maintained list\|code-ownership" argus/workflow/protocols/codebase-health-audit.md
# Expected: 5 tiers present

# F5: 3 non-trading fingerprint examples
grep -c "Pricing Engine Example\|A/B Test Cohort Example\|ML Model Recommendation Example" argus/workflow/protocols/codebase-health-audit.md
# Expected: 3

# F6: generalized absorption axes
grep -rh "work-execution state\|incoming-work size" argus/workflow/protocols/campaign-orchestration.md | wc -l
# Expected: ≥ 2

# F7: 3 stage-flow formats
grep -c "^## Format [123]:" argus/workflow/templates/stage-flow.md
# Expected: 3

# F8: closed-item terminology
grep -rh "closed-item" argus/workflow/protocols/codebase-health-audit.md | wc -l
# Expected: ≥ 2

# F9: squash-merge caveat
grep -rh "squash" argus/workflow/protocols/codebase-health-audit.md
# Expected: ≥ 1

# F10: 7-point-check appendix conditional framing
grep -B1 -A2 "appendix applies only when\|conditionally applies" argus/workflow/protocols/campaign-orchestration.md | head -5
# Expected: ≥ 1 match
```

Capture all 10 outputs in close-out as the F1–F10 coverage table.

## Constraints

- **Do NOT modify** any path under `argus/argus/`, `argus/tests/`, `argus/config/`, `argus/scripts/`. Triggers escalation criterion A1.
- **Do NOT modify** Sessions 0–5 outputs. They are stable. The audit expansion REFERENCES them; does not modify them.
- **Do NOT codify the safety-tag taxonomy** as a recommended mechanism anywhere. The 4 tags appear ONLY in §2.9 (Anti-pattern addendum) with explicit rejection-framing. Triggers escalation criterion B3 if the taxonomy creeps back as a recommended pattern.
- **Do NOT use** ARGUS-specific terminology ("DEF" universally, "trading session" universally, "boot commit" universally) without contextual framing. F1/F4/F5/F8/F9 generalized terminology applies throughout. Triggers escalation criterion B4 if the F1–F10 coverage table cannot enumerate addressing locations.
- **Do NOT phrase the phase-2-validate.py invocation advisorially.** Imperative gate language ("Phase 2 cannot complete until...", "MUST run...", "before proceeding to Phase 3..."). Triggers escalation criterion C2.
- **Do NOT modify** files outside the explicit list (codebase-health-audit.md major expansion; sprint-planning.md one-line cross-reference). Any other modification triggers scope-creep escalation per D3.
- **Do NOT** introduce new top-level sections beyond Phase 1 / Phase 2 / Phase 3 + their sub-sections. The protocol's macro-structure is defined.

## Test Targets

No executable code, no tests. Verification is grep-based per sub-phase + the final F1–F10 sweep.

## Definition of Done

- [ ] Sub-Phase 1: Phase 1 has 3 sub-sections (1.1, 1.2, 1.3); F8 closed-item terminology applied
- [ ] Sub-Phase 2: Phase 2 has 9 sub-sections (2.1–2.9); §2.7 hot-files has 5 tiers (F4); §2.8 has imperative gate language for `phase-2-validate.py`; §2.9 anti-pattern addendum present with rejection-framing
- [ ] Sub-Phase 3: Phase 3 has 9 sub-sections (3.1–3.9); §3.3 has all 3 non-trading fingerprint examples (F5); §3.8 has F9 squash-merge caveat
- [ ] Sub-Phase 4: sprint-planning.md cross-reference present; F1–F10 coverage table in close-out
- [ ] codebase-health-audit.md workflow-version is 2.0.0 (major bump)
- [ ] All Origin footnotes present
- [ ] No safety-tag taxonomy outside §2.9 addendum
- [ ] No ARGUS-specific terminology without contextual framing (per F1/F4/F5/F8 generalization)
- [ ] All verification grep commands run; outputs captured in close-out
- [ ] **F1–F10 coverage table in close-out** explicitly maps each F# to its addressing file/section across the entire sprint
- [ ] No scope creep
- [ ] Close-out report at `argus/docs/sprints/synthesis-2026-04-26/session-6-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Sessions 0–5 outputs untouched | Comprehensive diff of all prior-session-modified files; expect empty |
| ARGUS runtime untouched | `git diff HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/` returns empty |
| Bootstrap-index untouched (no new entries this session) | `git diff HEAD argus/workflow/bootstrap-index.md` returns empty |
| Audit version major bump | `head -3 argus/workflow/protocols/codebase-health-audit.md \| grep "workflow-version: 2.0.0"` returns 1 match |
| Anti-pattern addendum present + framed as rejection | `grep -B1 -A4 "Anti-pattern\|do not reinvent" argus/workflow/protocols/codebase-health-audit.md` shows the addendum with rejection-framing context |
| Imperative gate language for phase-2-validate.py | `grep -B2 -A2 "phase-2-validate\.py" argus/workflow/protocols/codebase-health-audit.md \| grep -E "(cannot complete\|MUST\|before proceeding)"` returns ≥ 1 |
| F1–F10 coverage verified | Close-out contains explicit F# → file/section table |
| sprint-planning.md cross-reference present + minor version bump | `grep "campaign-orchestration\.md" argus/workflow/protocols/sprint-planning.md` returns ≥ 1; version header bumped |
| 3 non-trading fingerprint examples | `grep -c "Pricing Engine Example\|A/B Test Cohort Example\|ML Model Recommendation Example" argus/workflow/protocols/codebase-health-audit.md` = 3 |
| 5 hot-files tiers | F4 grep returns 5 tier matches |

## Close-Out

Follow `.claude/skills/close-out.md`. **The close-out for this session is the sprint's final session close-out**; it must include the F1–F10 coverage table.

Write close-out to `argus/docs/sprints/synthesis-2026-04-26/session-6-closeout.md`.

The close-out's structured-closeout JSON appendix should include in the `judgment_calls` field a note that the major version bump (1.0.0 → 2.0.0) reflects the substantive addition of Phase 2 + Phase 3 content, not a backward-incompatible change to Phase 1.

The close-out's "F1–F10 Coverage Table" section format:

```markdown
## F1–F10 Coverage Table

| # | Finding | Addressing file(s) / section(s) |
|---|---|---|
| F1 | "Work Journal conversation" → "campaign coordination surface" | `protocols/campaign-orchestration.md` (preamble + §§1, 4); `protocols/codebase-health-audit.md` §3.4; `templates/work-journal-closeout.md` Hybrid Mode |
| F2 | recurring-event-driven framing | `protocols/operational-debrief.md` §1 (3 patterns) |
| F3 | "execution-anchor commit" not "boot commit" | `protocols/operational-debrief.md` §2 |
| F4 | tiered hot-files operationalizations | `protocols/codebase-health-audit.md` §2.7 (5 tiers) |
| F5 | 3 non-trading fingerprint examples | `protocols/codebase-health-audit.md` §3.3 (pricing, A/B, ML) |
| F6 | generalized absorption axes | `protocols/campaign-orchestration.md` §1 (work-execution state, incoming-work size) |
| F7 | stage-flow has 3 formats | `templates/stage-flow.md` (ASCII, Mermaid, ordered-list) |
| F8 | closed-item terminology in Phase 1 spot check | `protocols/codebase-health-audit.md` §1.1 |
| F9 | squash-merge caveat on git-commit-body pattern | `protocols/codebase-health-audit.md` §3.8 |
| F10 | 7-point-check appendix conditional framing | `protocols/campaign-orchestration.md` §10 (appendix preamble) |
```

If any F# cannot be confidently mapped, that's an escalation criterion B4 trigger.

**Commit pattern:**
```bash
cd argus/workflow
git add protocols/codebase-health-audit.md protocols/sprint-planning.md
git commit -m "synthesis-2026-04-26 S6: codebase-health-audit major expansion 1.0.0 -> 2.0.0 + sprint-planning cross-reference"
git push origin main

cd ..
git add workflow docs/sprints/synthesis-2026-04-26/session-6-closeout.md
git commit -m "synthesis-2026-04-26 S6: advance workflow submodule + final close-out (sprint complete)"
git push
```

## Tier 2 Review (Mandatory — @reviewer Subagent)

This is the sprint's final Tier 2 review. Standard invocation. Review writes to `argus/docs/sprints/synthesis-2026-04-26/session-6-review.md`.

**The @reviewer for this session should be especially thorough.** The audit-expansion is the structural defense against future audits reinventing the rejected patterns; its content is load-bearing across the metarepo.

## Session-Specific Review Focus (for @reviewer)

1. **F1–F10 coverage table** is the primary deliverable verification. Every F# must map to a concrete file + section; missing maps trigger escalation criterion B4.
2. **Anti-pattern addendum (§2.9) framing** — verify the safety-tag taxonomy appears ONLY in this addendum AND with explicit rejection-framing ("empirically overruled," "do not reinvent," "rejected"). Reintroduction as a recommended pattern is escalation criterion B3.
3. **Imperative gate language** for `phase-2-validate.py` (§2.8). "Cannot complete until," "MUST run," "before proceeding" — verify imperative phrasing. Advisory phrasing ("you may run") is escalation criterion C2.
4. **3 non-trading fingerprint examples** (§3.3) — pricing engine, A/B test, ML model. Each with concrete mechanism-signature articulation.
5. **5 hot-files tiers** (§2.7) — recent-bug, recent-churn, post-incident, maintained list, code-ownership.
6. **F8 closed-item terminology** consistent in §1.1.
7. **F9 squash-merge caveat** in §3.8.
8. **No ARGUS-specific terminology** appearing universally (DEF, trading session, boot commit) — appears only in contextual framing (e.g., as one example among several, or in §5 of operational-debrief.md).
9. **Major version bump (2.0.0)** correctly applied; rationale documented in close-out.
10. **All cross-references resolve** — Phase 3's references to Sessions 3/4/5 outputs all point at existing files.

## Sprint-Level Regression Checklist (for @reviewer)

See review-context.md §"Embedded Document 3." For Session 6, the FINAL session: ALL R1–R20 checks should pass. The Tier 2 reviewer for this session runs the full checklist (per the "Tier 2 Reviewer Workflow" §4 of the regression checklist) and produces a comprehensive verdict. Particular focus on R12 (F1–F10 coverage), R13 (no safety-tag), R8 (workflow-version 2.0.0), R14 (cross-references all resolve).

## Sprint-Level Escalation Criteria (for @reviewer)

See review-context.md §"Embedded Document 4." For Session 6, all escalation triggers apply with extra weight given the integrative nature of the session: B3 (safety-tag reintroduction — highest-risk this session), B4 (F1–F10 coverage), C2 (validator gate phrasing), A3 (RETRO-FOLD content semantic regression — verify universal.md untouched), D3 (scope creep into prior sessions' files).
