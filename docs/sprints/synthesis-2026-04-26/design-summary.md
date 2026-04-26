# Synthesis Sprint (2026-04-26) — Design Summary

> Phase B compaction-insurance artifact. If the planning conversation loses
> context, this document alone is sufficient to regenerate every downstream
> artifact (sprint spec, spec-by-contradiction, session breakdown, escalation
> criteria, regression checklist, doc update checklist, implementation
> prompts, review prompts, work journal handoff prompt).
>
> Target repo: `claude-workflow` metarepo (https://github.com/stevengizzi/claude-workflow)
> Sprint package home: `argus/docs/sprints/synthesis-2026-04-26/`
> Execution mode: human-in-the-loop
> Adversarial review: not required; synthetic-stakeholder pass for the audit
> protocol expansion is folded into Phase B (see §"Synthetic-stakeholder pass" below)

---

## Sprint Goal

Fold the unsynthesized post-RETRO-FOLD process learnings (3 audit-era
evolution notes from 2026-04-21 + 4 floating P-candidates P26–P29 +
~5 process patterns invented during Sprint 31.9 campaign-close) into the
`claude-workflow` metarepo so that the patterns auto-fire on subsequent
campaigns and sprints — not as documents that depend on operator memory.

The sprint also lands one keystone wiring change
(`templates/implementation-prompt.md` Pre-Flight step 1 reads
`.claude/rules/universal.md`) that retroactively activates RETRO-FOLD's
P1–P25 RULE coverage, which is currently weakly wired and depends on
Claude Code's incidental discovery of the rules file.

---

## Session Breakdown

### Session 0 (argus-side, ≤15 min, ARGUS-doc-only)

**Scope:** Append P28 + P29 retrospective candidates to
`SPRINT-31.9-SUMMARY.md` §Campaign Lessons so the synthesis input set is
durable before the metarepo work runs. Optional: add `## Rules` section
to ARGUS's `CLAUDE.md` if not already present.

- **Creates:** none
- **Modifies:** `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`;
  *optional:* `argus/CLAUDE.md`
- **Integrates:** N/A (foundational input-set commit; no prior session)
- **Parallelizable:** false (must precede Sessions 1 + 2 so the synthesis
  references a stable input)

### Session 1 (metarepo, mechanical, ≤90 min)

**Scope:** Land the keystone Pre-Flight wiring + new RULE entries +
skill/template extensions + status-stamp the 3 evolution notes. All
edits are well-bounded extensions to existing files. No new files.

- **Creates:** none
- **Modifies:**
  - `claude/rules/universal.md` — RULE-051 (P26), RULE-052 (P27),
    RULE-053 (P29), RULE-038 5th sub-bullet (P28)
  - `claude/skills/close-out.md` — strengthen Step 3 (FLAGGED blocks
    both commit and push, ID3.4)
  - `templates/implementation-prompt.md` — **keystone**: Pre-Flight
    step 1 (read `.claude/rules/universal.md`); operator-choice
    block (N3.5); no-cross-referencing rule (ID3.1); section-order
    discipline (N3.8)
  - `templates/review-prompt.md` — **keystone**: Pre-Flight step
    (read universal.md, symmetric to implementation prompt)
  - `templates/work-journal-closeout.md` — Hybrid Mode section (N3.6)
  - `templates/doc-sync-automation-prompt.md` — Between-Session
    Doc-Sync section (P34)
  - `scaffold/CLAUDE.md` — add `## Rules` section pointing at
    `.claude/rules/universal.md` (defensive backup wiring)
  - `evolution-notes/README.md` — synthesis status convention
  - `evolution-notes/2026-04-21-argus-audit-execution.md` —
    additive `**Synthesis status:**` header line only
  - `evolution-notes/2026-04-21-debrief-absorption.md` — same
  - `evolution-notes/2026-04-21-phase-3-fix-generation-and-execution.md` — same
- **Integrates:** N/A (mechanical extensions; no upstream session output to wire)
- **Parallelizable:** false (Session 2 depends on Session 1's RULE
  numbering being stable)

### Session 2 (metarepo, new content + audit expansion, ≤120 min)

**Scope:** Create the new protocols + templates and major-expand
`codebase-health-audit.md`. This is the design-judgment-heavy session.

- **Creates:**
  - `protocols/campaign-orchestration.md` (NEW) — covers campaign
    absorption (N2.1), supersession (N2.4), authoritative-record
    preservation (ID2.1), Work-Journal-per-campaign heuristic (ID2.2),
    cross-track close-out (ID2.5), pre-execution gate (ID2.6),
    naming conventions (ID2.7), DEBUNKED finding status (ID2.8),
    absorption-vs-sequential decision matrix (OQ2.1), campaign-close
    plan + 2-session SPRINT-CLOSE option (P30, P33), 7-point-check
    appendix for campaign-tracking conversations (P32)
  - `protocols/operational-debrief.md` (NEW) — abstract pattern
    (P31), boot-commit correlation as the actual generalizable
    insight (replaces rejected safety-tag taxonomy), references
    project-specific debrief protocols
  - `templates/stage-flow.md` (NEW) — DAG artifact template for
    multi-track campaigns (N2.3, N2.5, OQ2.2, OQ2.6); covers
    fork-join staging as a documented sub-case
  - `templates/scoping-session-prompt.md` (NEW) — read-only
    scoping session that produces both findings and a generated
    fix prompt (N2.2, ID2.4)
  - `scripts/phase-2-validate.py` (NEW) — CSV linter (~50 lines):
    row column-count, decision-value canonical form, fix-now has
    fix_session_id, FIX-NN-kebab-name format. **Does NOT validate
    safety tags** — that taxonomy was rejected.
- **Modifies:**
  - `protocols/codebase-health-audit.md` (1.0.0 → 2.0.0) — major
    expansion: Phase 1 (DEF-triage spot check S1.1, custom-structure
    rule S1.2, session-count budget S1.3); Phase 2 (CSV integrity +
    override table N3.2 + scale-tiered tooling OQ3.2 + N1.4 +
    N1.5 + ID1.1 + S1.4 + ID1.3 + hot-files concept ID1.5 +
    rejected-pattern addendum for safety-tag taxonomy + Phase
    Validate gate); Phase 3 (file-overlap-only DAG scheduling
    [N3.1 minus safety-matrix half] + fingerprint-before-behavior-change
    [N3.4/N1.2] + sort_findings_by_file [ID3.2] + Work Journal
    branch [S3.5] + scope-extension home + numbering rules [ID1.4] +
    git-commit-body-as-state-oracle as OPTIONAL [N3.7] + cardinality
    [OQ3.4]). **Drops: safety-tag core+modifier split, action-type
    routing for non-standard tags [N3.3 moot], safety-tag session
    resolution [ID3.3 moot].**
  - `protocols/sprint-planning.md` — minor: cross-reference to
    `campaign-orchestration.md`
  - `protocols/impromptu-triage.md` — extension: two-session
    scoping variant referencing `templates/scoping-session-prompt.md`
  - `bootstrap-index.md` — add "Campaign Orchestration / Absorption /
    Close" routing; add "Operational Debrief" routing; new rows in
    Protocol Index + Template Index for the 4 new files
- **Integrates:**
  - Session 1's new RULE numbering (the new protocols cite
    RULE-038/049/051-053 by number)
  - Session 1's keystone Pre-Flight wiring (the new protocols' fix
    prompts inherit it via the implementation-prompt template)
- **Parallelizable:** false (depends on Session 1)

---

## Key Decisions

1. **Keystone wiring is the highest-leverage edit in the sprint.** A
   single Pre-Flight step ("read `.claude/rules/universal.md`") in
   `templates/implementation-prompt.md` + `templates/review-prompt.md`
   converts every existing and future RULE into auto-fire-on-session-start
   behavior. Retroactively activates RETRO-FOLD's P1–P25 coverage that
   currently depends on Claude Code's incidental file discovery.

2. **Safety-tag taxonomy REJECTED.** Empirically overruled in Sprint 31.9
   execution — the operator ran almost all fixes during active market
   sessions regardless of tag, using boot-commit correlation instead. The
   4-tag flat version, the proposed core+modifier split, and the routing
   workarounds (N3.3, ID3.3) are all dropped. Documented as a rejected
   pattern in `codebase-health-audit.md` Phase 2 with rationale, so the
   next audit doesn't reinvent it.

3. **Boot-commit correlation is the codified replacement.** Goes in
   `protocols/operational-debrief.md` reflecting current ARGUS reality
   (operator manually records). Subsection flags the recommended
   automation (live system writes boot commit to known location at
   startup) as project-specific; ARGUS-side automation is OUT of scope
   for this sprint but logged as an ARGUS deferred item.

4. **Hot-files concept retained.** Survives the safety-tag rejection
   because it's about review intensity (diagnostic-first / adversarial
   review), not scheduling. IMPROMPTU-04's adversarial review on
   `order_manager.py` is the cited evidence.

5. **Scope split into 3 sessions.** Compaction-risk scoring on the
   original "single-session" suggestion came in at ~41 (Critical).
   Session 0 trivial, Session 1 mechanical, Session 2 design-heavy.
   Session 1 lands first so RULE numbering is stable for Session 2.

6. **Auto-effect wiring is non-optional.** Every new file must be either
   (a) referenced by a routed protocol (so bootstrap-index discovery
   reaches it), or (b) symlinked into project `.claude/` (so Claude Code
   discovers it at session start). Sit-there docs are explicitly the
   anti-pattern this sprint is designed to avoid.

7. **Three new protocols, not two.** P30 (campaign-close), P32
   (7-point-check), and P33 (two-session SPRINT-CLOSE) all land in
   `protocols/campaign-orchestration.md`. P32 as a clearly-marked
   appendix titled "Per-session tracking checks (for the
   campaign-tracking conversation)" — keeps the meta-ness contained
   without inventing a fourth protocol file.

8. **`scripts/phase-2-validate.py` invoked as non-bypassable Phase 2
   gate.** Codebase-health-audit.md Phase 2 wording: "Phase 2 cannot
   complete until phase-2-validate.py exits zero on the CSV." Grep-detectable
   so a future audit-running session can verify the gate fired.

9. **Evolution-note status headers as additive metadata.** Each note
   gets a single new `**Synthesis status:** SYNTHESIZED in
   synthesis-2026-04-26 (commit X)` line at the top of the metadata
   block. Body left unchanged — preserves audit-trail integrity per the
   kickoff constraint.

10. **Workflow-version bumps:** `codebase-health-audit.md` 1.0.0 → 2.0.0
    (major; scope expansion); `claude/rules/universal.md` 1.0 → 1.1
    (additive RULEs); `templates/implementation-prompt.md` 1.2.0 → 1.3.0
    (keystone Pre-Flight); `templates/review-prompt.md` 1.1.0 → 1.2.0
    (keystone Pre-Flight); other extended files: minor bumps. New files
    start at 1.0.0.

---

## Scope Boundaries

### IN

- `claude-workflow` metarepo: 4 new files + ~10 file extensions +
  bootstrap-index updates
- ARGUS doc-only: 1-2 file edits (SPRINT-31.9-SUMMARY.md backfill;
  optional CLAUDE.md `## Rules` section)
- Synthetic-stakeholder pass on the new audit protocol content
  (Phase B sub-step before Phase C generation)

### OUT

- ARGUS runtime code, tests, configs (kickoff constraint)
- Modifications to existing RULE-038 through RULE-050 (sealed by
  RETRO-FOLD)
- Re-derivation of P1–P25 (already complete)
- Modifying the bodies of the 3 evolution notes (only additive
  metadata header allowed)
- Automating ARGUS's boot-commit logging (ARGUS code change, separately
  logged as ARGUS deferred item)
- Updating MuseFlow / Grove / other downstream projects' `CLAUDE.md`
  files to add `## Rules` section (per-project doc-sync, not metarepo work)
- Migration scripts for projects already using the rejected safety-tag
  taxonomy (only ARGUS used it; no migration burden expected)
- Tag creation in the metarepo (RETRO-FOLD deferred; same posture here)

---

## Regression Invariants

These must remain true after the sprint lands:

1. **RETRO-FOLD's P1–P25 metarepo additions are unchanged in body
   and unchanged in semantic intent.** RULE-038 acquires a 5th
   sub-bullet from P28; otherwise RULE-038 through RULE-050 are
   byte-for-byte preserved. Origin footnotes preserved verbatim.
2. **Existing metarepo files keep their existing structure.**
   Extensions are additive sections, not restructurings. Existing
   section anchors continue to work.
3. **`bootstrap-index.md` "Conversation Type → What to Read"** ordering
   and existing entries are preserved; new entries appended.
4. **Existing skill / template invocation patterns continue to work.**
   The keystone Pre-Flight addition extends the implementation-prompt
   template; it does NOT replace any existing Pre-Flight content.
5. **No metarepo source file is renamed, moved, or deleted.**
6. **Universal.md's symlink target on existing projects continues to
   resolve.** New RULEs land at end of existing structure; numbering
   contiguous (RULE-051 / 052 / 053).
7. **Body of the 3 evolution notes is untouched.** Only the metadata
   header gets a new line.

---

## File Scope

### Modify (metarepo-side, 10 files)

- `claude/rules/universal.md`
- `claude/skills/close-out.md`
- `templates/implementation-prompt.md`
- `templates/review-prompt.md`
- `templates/work-journal-closeout.md`
- `templates/doc-sync-automation-prompt.md`
- `scaffold/CLAUDE.md`
- `evolution-notes/README.md`
- 3× evolution notes (header line only)
- `protocols/codebase-health-audit.md`
- `protocols/sprint-planning.md`
- `protocols/impromptu-triage.md`
- `bootstrap-index.md`

### Create (metarepo-side, 5 files)

- `protocols/campaign-orchestration.md`
- `protocols/operational-debrief.md`
- `templates/stage-flow.md`
- `templates/scoping-session-prompt.md`
- `scripts/phase-2-validate.py`

### Modify (argus-side, 1-2 files)

- `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`
- *Optional:* `argus/CLAUDE.md`

### Do not modify

- ARGUS runtime code, tests, configs (any path under `argus/argus/`,
  `argus/tests/`, `argus/config/`, `argus/scripts/`)
- RETRO-FOLD's RULE-038 through RULE-050 bodies (only RULE-038 sub-bullet
  addition, per Origin footnote precedent)
- The 3 evolution notes' bodies (only metadata header addition)
- All other existing metarepo files not enumerated above

---

## Config Changes

No config changes. This is metarepo doc work — no Pydantic models, no
YAML files, no project-side runtime config.

---

## Test Strategy

**No new tests required.** This sprint produces no executable Python /
TypeScript that needs unit-test coverage. The only code addition is
`scripts/phase-2-validate.py`, which is a one-shot CLI utility — its
correctness is verified by:

- Manual smoke test: run against the ARGUS Sprint 31.9 audit Phase 2 CSV;
  verify it catches the 9 known column-drift rows
- Manual edge-case check: run against a malformed test CSV with each
  intended check failing; verify each check produces a row-by-row report

These are documented in the Session 2 implementation prompt as Definition-
of-Done items, not automated tests.

**Argus-side test invariant:** the SPRINT-31.9-SUMMARY.md edit is a
content-only change to a docs file. Does not affect pytest count.

**Metarepo-side test invariant:** the metarepo has no test suite of its
own. Quality is verified by:

- Tier 2 review of each session's diff
- Synthetic-stakeholder pass on the audit protocol expansion (Phase B)
- Spot-check that origin footnotes resolve to the cited evolution notes
  / P# / SPRINT-31.9 artifacts

---

## Runner Compatibility

- **Mode:** human-in-the-loop only. No runner config generation.
- **Parallelizable sessions:** none. Strict serial: Session 0 → 1 → 2.
- **Estimated token budget:** ~80–120K tokens per metarepo session
  (Session 1 mechanical, mostly diff edits; Session 2 generates ~5
  new files of moderate size + one large protocol expansion).
- **Runner-specific notes:** N/A.

---

## Dependencies

**Pre-Session-0 (entry conditions for the sprint):**

- ARGUS Sprint 31.9 sealed (it is, per `SPRINT-CLOSE-campaign-seal.md`)
- 3 evolution notes present in `workflow/evolution-notes/` (they are)
- RETRO-FOLD complete (it is, per RETRO-FOLD-closeout.md and
  metarepo commit `63be1b6`)
- Operator confirms safety-tag-taxonomy REJECTION (confirmed in
  Phase A pushback)
- Operator confirms boot-commit codification = current ARGUS reality
  (confirmed: manually recorded; automation deferred to ARGUS)

**Pre-Session-1 (depends on):**

- Session 0 has landed (P28+P29 in SUMMARY)

**Pre-Session-2 (depends on):**

- Session 1 has landed (RULE numbering stable; keystone Pre-Flight
  wiring committed; templates extended)

---

## Escalation Criteria

A Tier 2 reviewer should escalate to operator (not auto-fix) if any
of these surface:

1. **Origin-footnote integrity break:** any new metarepo addition is
   missing an Origin footnote, OR any existing RULE-038 through RULE-050
   Origin footnote is altered.
2. **Body modification of an evolution note:** any change to the body
   of `2026-04-21-*.md` beyond the additive header line.
3. **RETRO-FOLD content semantic change:** any change to RULE-038
   through RULE-050 that materially changes the meaning of the rule
   (sub-bullet addition for RULE-038/P28 is OK; everything else is
   ESCALATE).
4. **Bootstrap routing missed:** any new protocol file not added to
   `bootstrap-index.md` "Conversation Type → What to Read" + Protocol
   Index. Failure mode: protocol becomes sit-there doc, defeats the
   sprint's purpose.
5. **Keystone Pre-Flight not landed:** Session 1 close-out claims
   complete but `templates/implementation-prompt.md` does not contain
   a Pre-Flight step explicitly reading `.claude/rules/universal.md`.
   This is the single highest-leverage edit; missing it is sprint
   failure.
6. **Safety-tag content survives:** any reference to a 4-tag safety
   taxonomy or a core+modifier split in the new audit protocol that
   wasn't framed as a rejected-pattern addendum.
7. **ARGUS runtime code modified:** any commit to a path under
   `argus/argus/`, `argus/tests/`, `argus/config/`, or `argus/scripts/`.
   The kickoff constraint is hard.
8. **Workflow-version regression:** any file's version header bumped
   downward, or `codebase-health-audit.md` not bumped to 2.0.0 after
   major expansion.

---

## Doc Updates Needed (post-sprint)

**Metarepo-side (handled within Sessions 1 + 2):**
- Workflow-version bumps as enumerated in §Key Decisions #10
- bootstrap-index.md routing entries (Session 2)
- evolution-notes/README.md synthesis status convention (Session 1)
- 3× evolution-note status headers (Session 1)

**ARGUS-side (operator-handled, post-sprint):**
- Update ARGUS roadmap with the boot-commit-logging automation as a
  deferred item (out-of-scope for this sprint)
- *Optional:* update ARGUS CLAUDE.md with `## Rules` section if not
  already present
- Argus's submodule pointer to `workflow/` advances to the new
  metarepo HEAD after Sessions 1 + 2 land

**Other downstream projects (out-of-scope; operator's choice):**
- MuseFlow / Grove etc. CLAUDE.md `## Rules` section if not present
- Their submodule pointer advances when they next pull workflow/

---

## Synthetic-Stakeholder Pass

Per Phase A item 5 + Sprint Planning protocol step 8: run a synthetic-
stakeholder pass on the proposed `protocols/codebase-health-audit.md`
expansion (and the new `campaign-orchestration.md` since it's
substantively new) before generating Phase C artifacts. Stakeholder
roleplay: *"a developer on a non-ARGUS project — say a typical SaaS
backend with 50K LOC, 4 contributors, no live operational concerns —
running their first codebase audit using this protocol."* Find:

- Items that assume ARGUS-specific structure (file overlap matrix
  algorithm assumes Python/pytest; how does a TypeScript / Java project
  use it?)
- Items that assume operational-cycle constraints (every reference
  to "active trading session" needs to generalize to "live operational
  cycle" or be omitted from the universal protocol)
- Items where the absence of a Work Journal conversation makes the
  protocol harder to follow than it should be
- Items where a non-trading project's debrief looks fundamentally
  different (cron job; web service; daily batch process)

Output: a brief findings list folded into the spec-by-contradiction
("explicitly NOT covered: X, Y, Z") + a sentence per protocol noting
"applicable to projects with [characteristics]; inapplicable to
[edge cases]".

This pass adds ~10 minutes to Phase B and protects against
over-codification of ARGUS-specific patterns.

---

## Artifacts to Generate (Phase C/D)

Per `protocols/sprint-planning.md` Phase C/D in order:

1. Sprint Spec
2. Specification by Contradiction (incorporates synthetic-stakeholder findings)
3. Session Breakdown (with Creates/Modifies/Integrates per session +
   compaction-risk scoring tables)
4. Sprint-Level Escalation Criteria (8 items above expanded)
5. Sprint-Level Regression Checklist (7 invariants above expanded)
6. Doc Update Checklist
7. Review Context File (single shared doc)
8. Implementation Prompt × 3 (Session 0 minimal, Session 1, Session 2)
9. Tier 2 Review Prompt × 3
10. Work Journal Handoff Prompt (human-in-the-loop mode)
11. *No runner config* (human-in-the-loop)

---

## Success Definition

The sprint succeeds when:

1. Every metarepo addition is committed and reachable from
   `bootstrap-index.md` (or symlinked into project `.claude/`).
2. The keystone Pre-Flight rule-loading step is present in
   `templates/implementation-prompt.md` and `templates/review-prompt.md`.
3. RETRO-FOLD's P1–P25 RULE coverage is now auto-fire (verified by:
   trace path from a fresh implementation prompt through Pre-Flight
   step 1 → universal.md is in context → all RULEs are available).
4. The 3 evolution notes carry SYNTHESIZED status headers pointing
   at this sprint.
5. P28 + P29 are durably captured in `SPRINT-31.9-SUMMARY.md`
   §Campaign Lessons.
6. RULE-051, RULE-052, RULE-053 are present in `claude/rules/universal.md`
   with origin footnotes citing P26 / P27 / P29.
7. RULE-038 carries its 5th sub-bullet for P28.
8. The 4 new files (`campaign-orchestration.md`,
   `operational-debrief.md`, `stage-flow.md`,
   `scoping-session-prompt.md`) are in place.
9. `scripts/phase-2-validate.py` runs cleanly against the Sprint 31.9
   audit CSV.
10. `codebase-health-audit.md` is at version 2.0.0 with the rejected-
    safety-tag-taxonomy addendum present and correctly framed.
