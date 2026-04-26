# Sprint synthesis-2026-04-26: Review Context File

> **This file is the single shared review context for all Tier 2 reviews of synthesis-2026-04-26 sessions.** Each implementation prompt's @reviewer subagent invocation points at this file by path. Do not duplicate this content in individual session review prompts — reference it.
>
> **Reviewer (or @reviewer subagent) Instructions:**
>
> 1. You are conducting a Tier 2 code review. This is a **READ-ONLY** session. Do NOT modify any source code, configuration, or documentation files. The ONE exception is the review report file you produce at `argus/docs/sprints/synthesis-2026-04-26/session-N-review.md` (or equivalent) — that file is your sole permitted write.
>
> 2. Follow the review skill in `.claude/skills/review.md`. Your review report MUST include the structured JSON verdict at the end, fenced with ` ```json:structured-verdict `, per the schema documented in the review skill.
>
> 3. Read this entire file (Sprint Spec + Specification by Contradiction + Regression Checklist + Escalation Criteria, all embedded below) BEFORE evaluating the session's diff. The four embedded documents define the contract the session is being reviewed against.
>
> 4. Read `.claude/rules/universal.md` and treat its contents as binding for this review (per RULE-013 read-only mode and the keystone Pre-Flight wiring landed in Session 1).
>
> 5. **Verdict determination:**
>    - **CLEAR:** All categories PASS. No findings with severity HIGH or CRITICAL.
>    - **CONCERNS:** All deliverables present, but one or more MEDIUM-severity findings exist (correctness concerns, terminology gaps, footnote misses) that don't rise to spec violation or escalation.
>    - **ESCALATE:** ANY trigger from the embedded "Sprint-Level Escalation Criteria" section is met, regression checklist failure, or "Do NOT modify" constraint violation.
>
> 6. **Compaction signals to watch for** (escalation criterion C3): incomplete edits across the diff, contradictory changes within the same file, references to non-existent files, repeated stub content, internal session state loss markers. If detected, verdict MUST be ESCALATE.
>
> 7. **Cross-cutting checks** (run on every session's review, not just the introducing session):
>    - **R6** (keystone Pre-Flight wiring present + imperative): every session starting from Session 1
>    - **R13** (safety-tag taxonomy ONLY in rejected-pattern addendum): every session
>    - **R20** (ARGUS runtime untouched): every session
>    See "Sprint-Level Regression Checklist" §4 "Tier 2 Reviewer Workflow" for the full per-session check list.
>
> 8. Write your review to `argus/docs/sprints/synthesis-2026-04-26/session-N-review.md` (where N is the session number being reviewed). Commit per the standard pattern in `claude/skills/review.md`.

---

## Embedded Document 1: Sprint Spec

The full Sprint Spec for synthesis-2026-04-26 follows. It defines the sprint's goal, deliverables, acceptance criteria, dependencies, decisions, and risks.

# Sprint synthesis-2026-04-26: Metarepo Synthesis of Audit-Era Process Learnings + Keystone Rule-Loading Wiring

## Goal

Fold the unsynthesized post-RETRO-FOLD process learnings (3 audit-era evolution notes from 2026-04-21 + 4 floating retrospective candidates P26–P29 + ~5 process patterns invented during Sprint 31.9 campaign-close) into the `claude-workflow` metarepo so that the patterns auto-fire on subsequent campaigns and sprints, not as documents that depend on operator memory. Land one keystone wiring change (`templates/implementation-prompt.md` + `templates/review-prompt.md` Pre-Flight step that loads `.claude/rules/universal.md`) that retroactively activates RETRO-FOLD's P1–P25 RULE coverage and ensures every future RULE auto-fires at session start.

## Scope

### Deliverables

1. **P28 + P29 retrospective candidates durably captured** in `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` §Campaign Lessons (Session 0).

2. **Keystone Pre-Flight rule-loading wiring** landed in `templates/implementation-prompt.md` and `templates/review-prompt.md` so every Claude Code session reads `.claude/rules/universal.md` deterministically (Session 1).

3. **Four new universal RULE entries** landed in `claude/rules/universal.md`: RULE-051 (mechanism-signature-vs-symptom-aggregate validation, P26), RULE-052 (CI-discipline drift on known-cosmetic red, P27), RULE-053 (FROZEN-marker defensive verification, P29). RULE-038 acquires a 5th sub-bullet for kickoff-statistics-as-directional-input (P28). (Session 1).

4. **Close-out skill strengthening** in `claude/skills/close-out.md` Step 3: FLAGGED self-assessment now blocks both commit AND push (formerly only push). (Session 1).

5. **Template extensions:** operator-choice block + no-cross-referencing rule + section-order discipline in `templates/implementation-prompt.md`; Hybrid Mode section in `templates/work-journal-closeout.md`; Between-Session Doc-Sync section in `templates/doc-sync-automation-prompt.md`. (Session 1).

6. **Scaffold CLAUDE.md backup wiring:** `## Rules` section added to `scaffold/CLAUDE.md` pointing at `.claude/rules/universal.md` (defensive layer in case Claude Code's auto-discovery is inconsistent). (Session 1).

7. **Evolution-note synthesis-status convention** documented in `evolution-notes/README.md`; three evolution notes (`2026-04-21-argus-audit-execution.md`, `2026-04-21-debrief-absorption.md`, `2026-04-21-phase-3-fix-generation-and-execution.md`) acquire a `**Synthesis status:** SYNTHESIZED in synthesis-2026-04-26 (commit X)` header line. Bodies untouched. (Session 1).

8. **Four new metarepo files** created (Session 2):
   - `protocols/campaign-orchestration.md` — covers campaign absorption, supersession convention, authoritative-record preservation, cross-track close-out, pre-execution gate, naming conventions, DEBUNKED finding status, absorption-vs-sequential decision matrix, two-session SPRINT-CLOSE option, and the 7-point-check appendix for campaign-tracking conversations.
   - `protocols/operational-debrief.md` — abstract pattern for recurring-event-driven knowledge streams; execution-anchor-commit correlation as the codified mechanism (replacing the rejected safety-tag taxonomy); references project-specific debrief implementations.
   - `templates/stage-flow.md` — DAG artifact template for multi-track campaigns; ASCII / Mermaid / ordered-list formats; covers fork-join staging and stage sub-numbering as documented sub-cases.
   - `templates/scoping-session-prompt.md` — read-only scoping session template that produces both findings AND a generated fix prompt for a follow-on session.

9. **`scripts/phase-2-validate.py`** — CSV linter (~50 lines) invoked as a non-bypassable gate before audit Phase 3 generation. Validates row column-count, decision-value canonical form, fix-now has fix_session_id, FIX-NN-kebab-name format. **Does NOT validate safety tags** (rejected taxonomy). (Session 2).

10. **`protocols/codebase-health-audit.md` major expansion** from 1.0.0 → 2.0.0 (Session 2). New content covers: Phase 1 (DEF Health Spot-Check S1.1, custom-structure rule S1.2, session-count budget S1.3); Phase 2 (CSV integrity + override table N3.2, scale-tiered tooling OQ3.2, operator-judgment-commit pattern N1.4, approval-heavy with hot-file carve-out N1.5, combined doc-sync ID1.1, in-flight triage amendment ID1.3, hot-files concept tiered operationalizations per F4, rejected-pattern addendum for 4-tag safety taxonomy, `phase-2-validate.py` non-bypassable gate); Phase 3 (file-overlap-only DAG scheduling [N3.1 minus safety-matrix], fingerprint-before-behavior-change with 3 non-trading examples per F5, sort_findings_by_file ID3.2, coordination-surface branch per F1, scope-extension home, contiguous numbering rules ID1.4, git-commit-body-as-state-oracle as OPTIONAL with caveat per F9, fix-group cardinality OQ3.4). Drops: safety-tag core+modifier split, action-type routing N3.3, safety-tag session resolution ID3.3.

11. **`protocols/impromptu-triage.md` extension:** two-session scoping variant referencing `templates/scoping-session-prompt.md`. (Session 2).

12. **`protocols/sprint-planning.md` cross-reference** to `campaign-orchestration.md`. (Session 2).

13. **`bootstrap-index.md` routing entries** for "Campaign Orchestration / Absorption / Close" and "Operational Debrief"; Protocol Index rows for the two new protocols; Template Index rows for the two new templates. (Session 2).

14. **All new metarepo content uses generalized terminology** per F1–F10 findings from the synthetic-stakeholder pass. Specifically: "campaign coordination surface" instead of "Work Journal conversation" (F1); recurring-event-driven framing for `operational-debrief.md` (F2); "execution-anchor commit" instead of "boot commit" (F3); tiered hot-files operationalizations (F4); 3 non-trading examples for fingerprint-before-behavior-change (F5); generalized campaign-absorption axes (F6); ASCII/Mermaid/ordered-list formats for stage-flow (F7); "closed-item" instead of "DEF" in Phase 1 spot check (F8); squash-merge caveat on git-commit-body pattern (F9); conditional framing of 7-point-check appendix (F10). (Session 2).

### Acceptance Criteria

For each deliverable, the conditions that must be true for it to be complete:

**1. P28 + P29 captured in SUMMARY:**
- `git log argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` shows a Session 0 commit with message referencing P28 + P29
- `grep -c "P28 candidate\|P29 candidate" argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` returns ≥ 2
- The §Campaign Lessons section's existing P26 + P27 entries are unchanged (preserved verbatim — additive append only)

**2. Keystone Pre-Flight wiring:**
- `grep -A2 "Pre-Flight Checks" workflow/templates/implementation-prompt.md` shows step 1 explicitly references reading `.claude/rules/universal.md`
- Same for `workflow/templates/review-prompt.md`
- The keystone step says "binding for this session" or equivalent imperative wording — not advisory
- Both files have workflow-version bumped (implementation-prompt 1.2.0 → 1.3.0; review-prompt 1.1.0 → 1.2.0)

**3. RULE additions:**
- `grep "^RULE-051:\|^RULE-052:\|^RULE-053:" workflow/claude/rules/universal.md` returns 3 matches
- Each has an Origin footnote citing P26 / P27 / P29 + a concrete example
- RULE-038 has a 5th sub-bullet covering kickoff-vs-actual closeout disclosure (P28); existing 4 sub-bullets unchanged
- RULE-038 through RULE-050 bodies are byte-for-byte preserved (verifiable via diff against pre-sprint HEAD)
- universal.md version bumped 1.0 → 1.1

**4. Close-out skill strengthening:**
- `grep -B1 -A3 "FLAGGED" workflow/claude/skills/close-out.md` Step 3 wording explicitly says FLAGGED blocks BOTH commit AND push
- Existing "Do NOT push if self-assessment is FLAGGED" wording either replaced with stronger version or supplemented (no semantic regression)

**5. Template extensions:**
- `templates/implementation-prompt.md` contains: an "Operator Choice" subsection with the checkbox-block pattern, a "No Cross-Referencing" constraint in the Constraints section, and a "Section Order" discipline note
- `templates/work-journal-closeout.md` contains a "Hybrid Mode" section
- `templates/doc-sync-automation-prompt.md` contains a "Between-Session Doc-Sync" section
- All bumped to next minor version

**6. Scaffold CLAUDE.md:**
- `grep "## Rules" workflow/scaffold/CLAUDE.md` returns ≥ 1 match
- The Rules section contains an explicit instruction to read `.claude/rules/universal.md`

**7. Evolution-note synthesis status:**
- `evolution-notes/README.md` documents the synthesis-status convention with the canonical header format
- All 3 evolution notes have a `**Synthesis status:** SYNTHESIZED in synthesis-2026-04-26 (commit [SHA])` line in their header block
- The bodies of all 3 evolution notes are byte-identical to pre-sprint state (verifiable via `git diff` showing only the metadata-block addition)

**8. Four new files exist:**
- `protocols/campaign-orchestration.md` exists with: campaign-absorption section, supersession convention, authoritative-record preservation, cross-track close-out, pre-execution gate, naming conventions, DEBUNKED status, decision matrix, two-session SPRINT-CLOSE, 7-point-check appendix
- `protocols/operational-debrief.md` exists with: 3 recurring-event-driven patterns enumerated, execution-anchor-commit definition, project-specific implementation references
- `templates/stage-flow.md` exists with: ASCII format, Mermaid format, ordered-list format (each with worked example)
- `templates/scoping-session-prompt.md` exists with: read-only constraints, dual-artifact requirement (findings + generated fix prompt), structured findings template (code-path map / hypothesis verification / race conditions / root-cause statement / fix proposal / test strategy / risk assessment)
- All 4 files have workflow-version: 1.0.0 headers

**9. Validator script:**
- `scripts/phase-2-validate.py` exists and is executable
- Manual smoke test passes against the ARGUS Sprint 31.9 audit Phase 2 CSV (catches the 9 known column-drift rows)
- Manual edge-case test passes against a malformed test CSV (each of the 6 checks produces a row-by-row report on its specific failure)
- Script exits 0 on clean CSV; non-zero on any check failure

**10. Audit protocol expansion:**
- `protocols/codebase-health-audit.md` workflow-version is 2.0.0
- File contains explicit Phase 1, Phase 2, Phase 3 sections (vs the current Phase-1-only structure)
- Phase 2 contains a `### Anti-pattern (do not reinvent)` subsection covering the rejected 4-tag safety taxonomy with rationale citing this synthesis sprint
- Phase 2 contains tiered hot-files operationalizations (recent-bug count / recent-churn / post-incident subjects / maintained list / code-ownership signal) per F4
- Phase 3 references `phase-2-validate.py` as a non-bypassable gate
- Phase 3's fingerprint-before-behavior-change section leads with 3 non-trading examples (pricing engine / A/B test / ML model) before the ARGUS scoring example per F5
- Phase 3 uses "campaign coordination surface" terminology (not "Work Journal conversation") per F1
- All ARGUS-specific terminology (DEF, boot commit, trading session) is generalized or contextually framed per F1–F10

**11. Impromptu-triage extension:**
- `protocols/impromptu-triage.md` contains a section describing the two-session scoping variant (read-only scoping session → fix session) with explicit reference to `templates/scoping-session-prompt.md`
- File workflow-version bumped to next minor
- Cross-references RULE-039 (single-session 5-phase risky batch edit) to clarify the distinction

**12. Sprint-planning cross-reference:**
- `protocols/sprint-planning.md` contains a one-line cross-reference to `protocols/campaign-orchestration.md` (e.g., in the "Workflow Mode Integration" section or equivalent)

**13. Bootstrap routing:**
- `bootstrap-index.md` "Conversation Type → What to Read" section contains entries for "Campaign Orchestration" and "Operational Debrief"
- `bootstrap-index.md` Protocol Index table contains rows for `campaign-orchestration.md` and `operational-debrief.md`
- `bootstrap-index.md` Template Index table contains rows for `stage-flow.md` and `scoping-session-prompt.md`
- All entries follow the existing style of the index (no formatting drift)

**14. Generalized terminology (cross-cutting):**
- Tier 2 reviewer verifies during Session 2 review: any reference to "Work Journal conversation," "trading session," "boot commit," "DEF," or other ARGUS-specific terms in new metarepo content is either replaced with generalized terminology or contextually framed (e.g., "ARGUS uses DEF; other projects use Linear issues / GitHub issues / equivalent")
- Each F# finding is explicitly addressed in a way grep-detectable from the diff (Session 2 close-out enumerates F1–F10 with file/section per finding)

### Performance Benchmarks

Not applicable. This is metarepo doc work — no executable runtime to benchmark. The validator script runs in well under 1 second on any realistic-size audit CSV; that's the only execution surface and it doesn't warrant a formal benchmark.

### Config Changes

No config changes. This sprint touches no Pydantic models, no YAML files, and no project-side runtime configuration. The metarepo has no config layer of its own.

## Dependencies

**Pre-sprint (entry conditions, all confirmed):**
- ARGUS Sprint 31.9 sealed (verified via `SPRINT-CLOSE-campaign-seal.md` in argus repo)
- 3 evolution notes present in `workflow/evolution-notes/2026-04-21-*.md`
- RETRO-FOLD complete (verified via `RETRO-FOLD-closeout.md` + metarepo commit `63be1b6`)
- Operator confirms safety-tag taxonomy REJECTION (confirmed in Phase A pushback round 2)
- Operator confirms boot-commit codification reflects current ARGUS reality (manually recorded; automation deferred)
- Operator confirms 3-session split, P32-as-appendix, additive evolution-note status header, argus-side sprint package home, synthetic-stakeholder pass run during Phase B (all confirmed)

**Inter-session dependencies (within this sprint):**
- Session 1 depends on Session 0 (P28+P29 in SUMMARY) so the synthesis input set is durable when the metarepo work references it
- Session 2 depends on Session 1 (RULE numbering 051/052/053 stable; keystone Pre-Flight wiring committed; templates extended) so new protocols can cite RULEs by number and inherit auto-loaded universal rules

**External tools assumed available:**
- `git` for commits, diffs, log inspection
- `grep` for invariant verification
- Python 3.x for `phase-2-validate.py` (uses standard library only — no new dependencies)

## Relevant Decisions

Captured in full in the design summary §Key Decisions. Most consequential here:

- **Safety-tag taxonomy REJECTED** — empirically overruled in Sprint 31.9 execution; documented as a rejected pattern in `codebase-health-audit.md` Phase 2 with rationale, so the next audit doesn't reinvent it. Cascading: N3.3 (action-type routing) and ID3.3 (safety-tag session resolution) are MOOT.
- **Keystone Pre-Flight wiring is the highest-leverage edit** — single Pre-Flight step in `templates/implementation-prompt.md` + `templates/review-prompt.md` retroactively activates RETRO-FOLD's P1–P25 RULE coverage and ensures every future RULE auto-fires at session start. Currently RETRO-FOLD's coverage is weakly wired (only RULE-039 is inline-referenced from a template); after the keystone, the whole universal.md applies deterministically.
- **Boot-commit / execution-anchor-commit correlation replaces the safety-tag taxonomy as the operational-debrief mechanism.** Reflects current ARGUS reality (operator manually records); automation flagged as project-specific recommended-but-not-required.
- **Hot-files concept retained** because it's about review intensity, not scheduling. F4 generalizes it to tiered operationalizations.
- **3-session split** because original "single-session" estimate hit ~41 compaction-risk points (Critical, must split into 3+).
- **No new tests** — validator script verified by manual smoke check; keeping metarepo's current zero-test posture.
- **P32 (7-point-check) as appendix in `campaign-orchestration.md`**, not standalone protocol.
- **3 evolution notes get additive metadata header only** — bodies preserved per kickoff constraint.

## Relevant Risks

- **F1–F10 findings from synthetic-stakeholder pass.** Risk: Session 2's protocol drafts inadvertently use ARGUS-specific terminology, producing protocols that work for ARGUS but feel alien to a SaaS or web-services project. Mitigation: Session 2 implementation prompt enumerates F1–F10 by number as drafting requirements; Tier 2 review explicitly verifies generalized-terminology coverage. Session 2 close-out must enumerate which file/section addresses each F# finding.
- **Bootstrap routing miss.** Risk: a new protocol file is committed but `bootstrap-index.md` is not updated to route to it; the protocol becomes a sit-there doc, defeating the sprint's auto-effect goal. Mitigation: regression checklist item explicitly verifies bootstrap-index has a routing entry per new protocol; Session 2 implementation prompt has bootstrap-index updates as a final mandatory step.
- **Keystone wiring miss.** Risk: Session 1 close-out claims complete but the Pre-Flight rule-loading step is not actually present in `implementation-prompt.md` / `review-prompt.md`. This is sprint failure. Mitigation: regression checklist + escalation criterion + acceptance criterion 2 all check for the keystone explicitly.
- **RETRO-FOLD content semantic regression.** Risk: editing `claude/rules/universal.md` to add RULE-051/052/053 inadvertently changes RULE-038 through RULE-050 wording. Mitigation: regression-checklist item runs `git diff workflow-pre-sprint workflow/claude/rules/universal.md` and confirms only additive lines for RULE-038-050 (5th sub-bullet on RULE-038, all new sections appended after RULE-050).
- **Evolution-note body modification.** Risk: editing the metadata header inadvertently touches body content. Mitigation: regression-checklist item runs `git diff` against each evolution note and confirms changes are localized to the metadata block lines only.
- **Argus runtime code accidentally modified.** Risk: a doc-sync edit drifts into `argus/argus/`, `argus/tests/`, `argus/config/`, or `argus/scripts/`. Mitigation: hard escalation criterion (any commit touching these paths halts the sprint).
- **Workflow-version bump miss.** Risk: `codebase-health-audit.md` major-expanded but version not bumped to 2.0.0; downstream readers don't know the protocol changed shape. Mitigation: regression-checklist item; Session 2 close-out verifies version bumps.
- **`phase-2-validate.py` invocation not grep-detectable in audit protocol.** Risk: validator script lands but the protocol step that invokes it is phrased advisorially ("you may run...") instead of imperatively ("Phase 2 cannot complete until..."), and a future audit treats it as optional. Mitigation: acceptance criterion 10 + Tier 2 review focus item both verify the imperative phrasing.

## Session Count Estimate

**3 sessions**, ~225 minutes total operator-attended time:

- **Session 0** (argus-side, ≤15 min): P28+P29 SUMMARY backfill + optional ARGUS CLAUDE.md `## Rules` section
- **Session 1** (metarepo mechanical, ≤90 min): keystone Pre-Flight wiring + RULEs + skill/template extensions + scaffold + evolution-notes README + status-stamp 3 notes
- **Session 2** (metarepo new content + audit expansion, ≤120 min): 4 new files + audit major expansion + impromptu-triage extension + sprint-planning cross-reference + validator script + bootstrap-index updates + F1–F10 generalized-terminology coverage

No frontend sessions, so no visual-review fix budget.

Compaction-risk scoring per session:
- **Session 0:** ~3 points (1 file modified + 1 file in pre-flight reads + 0.5 tests). Low risk.
- **Session 1:** ~24 points (10 files modified × 1 + 6 files in pre-flight reads + complex integration with RETRO-FOLD's existing structure +3 + medium-large file `implementation-prompt.md` already at ~270 lines). Medium-High; manageable because edits are mostly additive.
- **Session 2:** ~38 points (5 files created × 2 + 4 files modified × 1 + 12 files in pre-flight reads + complex integration with bootstrap-index + Session 1's outputs +3 + large new file `campaign-orchestration.md` expected ~250+ lines + large expansion of `codebase-health-audit.md` ~400+ lines × 2). High; at the edge of "must split" threshold. **Mitigation:** Session 2's implementation prompt structures the work as 4 distinct phases (existing-file extensions first → 4 new files → bootstrap routing → final F1–F10 verification) with explicit sub-checkpoints, allowing a mid-session pause if context pressure surfaces. Each new file is self-contained (no cross-file logic), so Claude Code can serialize them naturally.

If Session 2 hits compaction during execution, the design summary + Phase A scratchpad + spec are sufficient to resume in a fresh session with no loss of design state.

---

## Embedded Document 2: Specification by Contradiction

The full Specification by Contradiction for synthesis-2026-04-26 follows. It defines the explicit boundaries — what this sprint does NOT do.

# Sprint synthesis-2026-04-26: What This Sprint Does NOT Do

This document defines the explicit boundaries of synthesis-2026-04-26. It prevents scope creep during Sessions 0/1/2 and gives the Tier 2 reviewer clear failure conditions to check.

The sprint's scope is unusually wide (3 evolution notes + 4 P-candidates + 5 process-pattern candidates → 14 deliverables across the metarepo + minor argus-doc work). Without sharp boundaries, scope creep is the most likely failure mode. This document is the contract that prevents it.

---

## Out of Scope

These items are related to the sprint goal but explicitly excluded:

1. **Re-derivation or re-classification of P1–P25.** RETRO-FOLD already synthesized these into RULE-038 through RULE-050 + skill/template additions. Origin footnotes preserved. Any session that touches RULE-038–050 bodies (other than appending RULE-038's 5th sub-bullet for P28) escalates.

2. **Modifications to the bodies of the 3 evolution notes.** The notes are the audit trail. Only the additive `**Synthesis status:**` metadata header line is permitted. Body content (every line below the metadata block) is byte-frozen. Any session that produces a diff touching evolution-note body lines escalates.

3. **ARGUS runtime code, tests, or configuration changes.** This is metarepo + argus-doc work only. No commits under `argus/argus/`, `argus/tests/`, `argus/config/`, or `argus/scripts/`. The hard constraint is per the kickoff and is a Tier 2 escalation trigger.

4. **Codification of the rejected 4-tag safety taxonomy or its core+modifier expansion.** Safety-tag taxonomy was empirically overruled in Sprint 31.9 execution (operator ran fixes during active market sessions regardless of tag, used boot-commit correlation instead). The rejection is documented as a `### Anti-pattern (do not reinvent)` addendum in `codebase-health-audit.md` Phase 2 — that's the only place safety-tag taxonomy appears in new content. Any session that introduces a safety-tag schema, adds modifier tags, or codifies safety-tag routing logic in the new protocols escalates.

5. **Automating ARGUS's boot-commit logging.** `protocols/operational-debrief.md` documents the execution-anchor-commit correlation pattern reflecting current ARGUS reality (operator records manually). The protocol flags the recommended automation as project-specific and out of scope for this sprint. Implementing automation in ARGUS code is a separate ARGUS deferred item, not a synthesis sprint deliverable.

6. **Updates to non-ARGUS project `CLAUDE.md` files.** The metarepo cannot reach into MuseFlow / Grove / other downstream projects' `CLAUDE.md` files. Updating them with a `## Rules` section is per-project doc-sync that operators handle on their own time. The metarepo-side change is `scaffold/CLAUDE.md` — that affects only NEW projects bootstrapped after this sprint lands.

7. **Migration tooling for projects already using the rejected safety-tag taxonomy.** Only ARGUS adopted it (and only briefly during the Sprint 31.9 audit). Zero migration burden expected. No migration script, no automated rewrite, no compatibility shim.

8. **Metarepo test-suite introduction.** The metarepo has no `tests/` folder. The validator script (`scripts/phase-2-validate.py`) is verified by manual smoke check, not by automated test. Introducing a test framework, CI pipeline, or test-runner config to the metarepo is a separate strategic-check-in topic, not a synthesis sprint deliverable.

9. **Metarepo tag convention.** RETRO-FOLD deferred this; same posture here. Sprint 31.9-retro-fold could have been tagged at commit `63be1b6`; this sprint could equally tag `synthesis-2026-04-26` at its eventual commit. Neither happens in this sprint. Future sprint adopts a tagging policy.

10. **Generation pre-flight gate (N1.3 from the audit-execution evolution note).** Self-flagged speculative in the source note. No execution evidence yet. Defer to next strategic check-in. Listed in `evolution-notes/README.md` as "patterns reviewed and deferred pending more execution evidence."

11. **Cognitive-limit ceiling on parallel sessions (N3.F from phase-3-fix-generation note).** Explicitly rejected by operator in Sprint 31.9 audit. The metarepo stays silent on parallel-session count caps; operator preference is project-specific.

12. **Specific issue-tracker integrations.** Protocols mention Linear / GitHub Issues / Jira as examples but ship no integrations, no API calls, no automation. The phrase "campaign coordination surface" (per F1) names what each option must provide; not how to implement.

13. **Specific project-side operationalizations of hot-files thresholds.** Per F4, the audit protocol offers tiered approaches (recent-bug count / recent-churn / post-incident subjects / maintained list / code-ownership signal); the project picks one and documents it in the project's `.claude/rules/`. The metarepo does not pick a default threshold or recommend one combination over another.

14. **Adversarial review on this sprint.** Standard Tier 2 sufficient per kickoff. The synthetic-stakeholder pass already ran during Phase B (findings F1–F10 folded into spec). No additional adversarial review conversation needed.

15. **Runner-config generation.** Execution mode is human-in-the-loop. No `runner-config.yaml` produced. Work Journal Handoff Prompt produced instead.

16. **Tag-creation in argus repo.** The synthesis sprint produces commits but no git tags. Argus-side commits land on `main` directly per existing convention.

17. **Refactoring of existing metarepo file structure.** The synthesis is purely additive: new files added, existing files extended. No file moves, no renames, no directory restructuring. The repository layout (protocols/, templates/, claude/, runner/, schemas/, scripts/, scaffold/, evolution-notes/) is preserved.

18. **Updates to runner code (`runner/sprint_runner/`).** Runner is touched only if a new schema or new template breaks runner expectations. None of the additions in this sprint should affect runner behavior — all new files are doc/template/protocol work. If runner code modification appears necessary mid-sprint, escalate (likely indicates scope drift).

## Edge Cases to Reject

The implementation should NOT handle these cases:

1. **An evolution-note body has a typo or factual error discovered mid-sprint.** Do NOT fix it. The note is the audit trail; preserve verbatim. Log as a deferred observation in the close-out for separate strategic-check-in handling.

2. **A RETRO-FOLD RULE has unclear wording discovered mid-sprint.** Do NOT clarify it. RULE-038 through RULE-050 bodies are sealed. Log as a deferred observation.

3. **The synthetic-stakeholder pass surfaces a finding F11 mid-Session-2.** Do NOT fold it into the implementation. F1–F10 are the closed set. Any new finding that emerges during implementation logs as deferred observation in the close-out, surfaces in the Tier 2 review, and feeds into a possible follow-on sprint or strategic check-in.

4. **An ARGUS-specific term appears in new metarepo content and Claude Code judges it "obvious enough" to leave un-generalized.** REJECT — generalize per F1–F10 or contextually frame as an example. The Tier 2 reviewer explicitly checks for this. "Obvious enough" is the failure mode; the synthetic-stakeholder pass exists specifically to catch it.

5. **A new RULE entry (051/052/053) feels like it overlaps with an existing RULE.** Do NOT consolidate. The disposition matrix in Phase A explicitly classified each as either novel (new RULE) or sub-bullet (extension to RULE-038). If the implementer's reading suggests further consolidation, log as a deferred observation; do not act unilaterally.

6. **The validator script `phase-2-validate.py` "needs" additional checks beyond the 6 specified.** Do NOT add. The 6 checks are the contract: row column-count, decision-value canonical form, fix-now has fix_session_id, FIX-NN-kebab-name format, plus the two structural row-integrity checks. Additional checks are scope creep. If the implementer believes a 7th check is critical, log as deferred observation.

7. **The bootstrap-index.md "Conversation Type → What to Read" section "should" be reorganized.** Do NOT reorganize. Append new entries in the existing structure. Restructuring the index is out of scope.

8. **A protocol cross-reference "should" link to a different existing protocol.** Do NOT add cross-references beyond those explicitly required by the deliverables. Cross-reference proliferation makes the metarepo harder to maintain. The minimal set of cross-references in the spec is the contract.

9. **The `## Rules` section added to `scaffold/CLAUDE.md` "should" also list specific rule numbers.** Do NOT enumerate specific RULEs in the scaffold section — it just says "this project's universal rules live in `.claude/rules/universal.md` and are auto-loaded at session start per the implementation prompt's Pre-Flight step." Enumerating RULEs in the scaffold creates a sync-burden every time RULEs are added; the keystone Pre-Flight wiring makes enumeration unnecessary.

10. **The `protocols/operational-debrief.md` "should" include a worked example of a market-session debrief.** Do NOT include trading-flavored worked examples in this protocol — that's exactly the over-applying-ARGUS-shape failure mode F2 protects against. Include 3 non-trading examples (deploy retrospective, post-incident review, weekly health review) and reference ARGUS's `docs/protocols/market-session-debrief.md` as one project-specific implementation.

## Scope Boundaries

### Do NOT modify

- `claude/rules/universal.md` RULE-001 through RULE-050 bodies (existing rules)
- `claude/rules/universal.md` Origin footnotes for RULE-038 through RULE-050 (sealed by RETRO-FOLD)
- `claude/skills/review.md` (no changes proposed; if implementation finds a "should" reason to touch it, escalate)
- `claude/skills/diagnostic.md`, `claude/skills/canary-test.md`, `claude/skills/doc-sync.md` (out of scope)
- `claude/agents/builder.md`, `claude/agents/reviewer.md`, `claude/agents/doc-sync-agent.md` (out of scope)
- `protocols/adversarial-review.md`, `protocols/tier-3-review.md`, `protocols/discovery.md`, `protocols/getting-started.md`, `protocols/document-seeding.md`, `protocols/strategic-check-in.md`, `protocols/notification-protocol.md`, `protocols/run-log-specification.md`, `protocols/spec-conformance-check.md`, `protocols/tier-2.5-triage.md`, `protocols/retrofit-survey.md`, `protocols/sprint-wrap-up-checklist.md`, `protocols/in-flight-triage.md`, `protocols/autonomous-sprint-runner.md` (out of scope; only `sprint-planning.md` cross-reference + `impromptu-triage.md` extension + `codebase-health-audit.md` major expansion are touched)
- `templates/sprint-spec.md`, `templates/spec-by-contradiction.md`, `templates/decision-entry.md`, `templates/fix-prompt.md`, `templates/spec-conformance-prompt.md`, `templates/tier-2.5-triage-prompt.md`, `templates/design-summary.md` (out of scope)
- `schemas/*.md` (out of scope)
- `runner/` directory (entirely out of scope)
- `scripts/setup.sh`, `scripts/sync.sh`, `scripts/scaffold.sh` (out of scope; only `phase-2-validate.py` is added)
- `CLASSIFICATION.md`, `MIGRATION.md`, `VERSIONING.md`, `README.md` (out of scope)
- The 3 evolution notes' bodies (only metadata header addition allowed)
- ARGUS runtime: any path under `argus/argus/`, `argus/tests/`, `argus/config/`, or `argus/scripts/`
- ARGUS sprint history, decision log, architecture document (these are touched by SPRINT-CLOSE-B, which already ran for Sprint 31.9; this synthesis sprint touches only the SUMMARY for P28+P29 backfill)

### Do NOT optimize

- The size of `protocols/codebase-health-audit.md` after expansion. Expansion is expected to take it from ~87 lines to ~400+ lines. That's a feature, not a problem to optimize against. The protocol is reference material; readers consult relevant sections, not the whole document.
- The number of cross-references between new protocols. Minimum-necessary set per the spec, no more.
- The number of examples in any new protocol. Each pattern gets the examples specified in F1–F10 (typically 3 non-ARGUS-flavored + 1 ARGUS-flavored). Adding more examples is scope creep.

### Do NOT refactor

- The existing structure of any file being modified. Extensions are additive sections in their natural location, not re-organizations of surrounding content.
- The bootstrap-index.md "Conversation Type → What to Read" section's existing entries. New entries are appended; existing entries unchanged.
- The Protocol Index / Template Index tables in `bootstrap-index.md`. New rows appended; existing rows unchanged.
- Any heading hierarchy in any modified file.

### Do NOT add

- New skills (`claude/skills/`)
- New agents (`claude/agents/`)
- New schemas (`schemas/`)
- New evolution notes (the 3 existing notes are status-stamped, not joined)
- New runner modules
- New scaffold templates beyond the `## Rules` section addition to existing `scaffold/CLAUDE.md`
- New top-level directories in the metarepo
- A `tests/` directory in the metarepo
- A `git tag` on either repo

## Interaction Boundaries

- This sprint does NOT change the behavior of: the existing `setup.sh` symlink logic; the runner's prompt-loading mechanism; the bootstrap-index routing pattern (we add entries, not change the routing protocol); the existing skill-invocation pattern in templates (existing skills still invoked the same way).
- This sprint does NOT affect: existing project `.claude/rules/universal.md` symlinks (they re-resolve to the updated metarepo file automatically; that's the desired auto-effect); existing project `CLAUDE.md` files (each project independently decides whether to add a `## Rules` section); ARGUS's runtime, paper-trading state, or operational schedule.
- This sprint does NOT alter: the existing close-out skill's Step 1 / Step 2 / Step 4 (only Step 3's FLAGGED-blocks-commit-and-push wording strengthened); the existing review skill's structure (no edits planned); the implementation-prompt template's existing Pre-Flight steps 2/3/4+ (the keystone is inserted as a NEW step 1, existing steps remain).

## Deferred to Future Sprints

| Item | Target | Tracking |
|------|--------|---------|
| Generation pre-flight gate (N1.3) | Next strategic check-in | Document in `evolution-notes/README.md` deferred-patterns note |
| Boot-commit logging automation in ARGUS | ARGUS deferred items list | Logged as ARGUS-side DEF (operator handles in argus repo) |
| Per-project `CLAUDE.md` `## Rules` updates (MuseFlow / Grove / other) | Per-project doc-sync (operator's choice) | Not formally tracked in metarepo |
| Metarepo test suite introduction | Next strategic check-in | Document in close-out as deferred observation |
| Metarepo tag convention | Next strategic check-in | Same |
| ARGUS-side `CLAUDE.md` `## Rules` section (if not already present) | Session 0 optional sub-task or argus-side doc-sync | If skipped in Session 0, log as ARGUS deferred item |
| Project-specific operationalizations of hot-files thresholds | Per-project judgment when each project runs its first audit | Documented in `codebase-health-audit.md` as the operator's responsibility |
| Issue-tracker integrations | Future strategic-check-in if demand surfaces | Not currently planned |
| ARGUS reconciliation-drift sprint (DEF-204 fix) | `post-31.9-reconciliation-drift` | Pre-existing, not affected by this sprint |
| Other post-31.9 sprints (component-ownership, reconnect-recovery, alpaca-retirement, 31B) | Per ARGUS roadmap | Pre-existing, not affected |

---

## Embedded Document 3: Sprint-Level Regression Checklist

The full Sprint-Level Regression Checklist for synthesis-2026-04-26 follows. It defines the cross-session invariants that the Tier 2 reviewer verifies on every session's review.

# Sprint synthesis-2026-04-26: Sprint-Level Regression Checklist

> Cross-session invariants. The Tier 2 reviewer runs every item below at each session's review (not just the session that introduced the relevant content). This catches regressions where a later session inadvertently undoes or weakens an earlier session's work.
>
> Distinct from **session-specific** regression checklists (embedded in each session's implementation prompt) which cover invariants relevant only to that session's diff.
>
> Each item: invariant statement → verification command → expected outcome → what counts as a violation. Most items are grep/diff-based (mechanical). Where judgment is needed, it's flagged.

---

## Section 1: Sealed-Content Invariants

These check that content marked "do not modify" (per kickoff constraints + spec-by-contradiction §"Do NOT modify") stays preserved across all 6 sessions.

### R1. RULE-001 through RULE-050 bodies preserved byte-for-byte (except RULE-038 5th sub-bullet)

**Verify (run at every session's review):**
```bash
git show <pre-sprint-sha>:workflow/claude/rules/universal.md > /tmp/pre.md
git show HEAD:workflow/claude/rules/universal.md > /tmp/post.md
diff /tmp/pre.md /tmp/post.md
```

**Expected:** Diff shows ONLY:
- Append at end of file: new sections containing RULE-051, RULE-052, RULE-053
- Inside RULE-038 block: insertion of 5th sub-bullet (precise wording per spec §3); existing 4 sub-bullets unchanged
- Header version bump `<!-- workflow-version: 1.0 -->` → `<!-- workflow-version: 1.1 -->`
- Header date bump

**Violation:** Any line change inside RULE-001 through RULE-050 bodies (excluding the RULE-038 sub-bullet append). Triggers escalation criterion A3.

---

### R2. RETRO-FOLD origin footnotes preserved verbatim

**Verify:**
```bash
git show <pre-sprint-sha>:workflow/claude/rules/universal.md | grep -B1 -A4 "Origin: Sprint 31.9 retro" > /tmp/pre-footnotes.txt
git show HEAD:workflow/claude/rules/universal.md | grep -B1 -A4 "Origin: Sprint 31.9 retro" > /tmp/post-footnotes.txt
diff /tmp/pre-footnotes.txt /tmp/post-footnotes.txt
```

Same check on:
- `workflow/claude/skills/close-out.md`
- `workflow/claude/skills/review.md`
- `workflow/protocols/sprint-planning.md`
- `workflow/templates/implementation-prompt.md`

**Expected:** All 25 RETRO-FOLD origin footnotes (P1–P25 references) byte-identical between pre-sprint and HEAD.

**Violation:** Any change to RETRO-FOLD's origin-footnote wording, even cosmetic (whitespace, capitalization, punctuation). Triggers escalation criterion A3.

---

### R3. Evolution-note bodies byte-frozen

**Verify (run after Session 2 + every subsequent session):**
```bash
for note in workflow/evolution-notes/2026-04-21-*.md; do
    pre=$(git show <pre-sprint-sha>:$note 2>/dev/null)
    post=$(git show HEAD:$note)
    # Strip metadata block (top section ending with first ---), compare bodies
    pre_body=$(echo "$pre" | awk 'BEGIN{p=0; sep=0} /^---$/{sep++; if(sep==2){p=1; next}} p')
    post_body=$(echo "$post" | awk 'BEGIN{p=0; sep=0} /^---$/{sep++; if(sep==2){p=1; next}} p')
    diff <(echo "$pre_body") <(echo "$post_body") || echo "BODY DIFFERS in $note"
done
```

**Expected:** Body content (lines below the metadata block's closing `---`) byte-identical pre/post across all 3 evolution notes. Only the metadata block has the additive `**Synthesis status:**` line.

**Violation:** Any change to body lines, including whitespace-only changes. Triggers escalation criterion A2.

---

### R4. ARGUS runtime / tests / configs not touched

**Verify (every session, especially Session 0):**
```bash
git diff <pre-sprint-sha>..HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/
```

**Expected:** Empty output. The ONLY argus-side changes permitted are:
- `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` (Session 0 P28+P29 backfill)
- `argus/CLAUDE.md` (Session 0 optional `## Rules` section)
- `argus/workflow` submodule pointer (operator advances after metarepo sessions land)

**Violation:** Any path matched. Triggers escalation criterion A1. **HARD constraint** — no judgment override.

---

### R5. RETRO-FOLD-touched skill/template additions preserved

**Verify:**
```bash
git diff <pre-sprint-sha>..HEAD -- workflow/claude/skills/review.md workflow/claude/skills/diagnostic.md workflow/claude/skills/canary-test.md workflow/claude/skills/doc-sync.md
```

**Expected:** review.md / diagnostic.md / canary-test.md / doc-sync.md unchanged across the sprint (none of these files appear in any session's modify list).

**Violation:** Any diff in these files. Escalates per spec-by-contradiction "Do NOT modify" list.

---

## Section 2: Structural Integrity Invariants

These verify that the sprint's intended structure (keystone wiring, bootstrap routing, version headers) is in place after the relevant session and remains stable through subsequent sessions.

### R6. Keystone Pre-Flight wiring present + imperative

**Verify (run at every session's review starting Session 1):**
```bash
# Implementation prompt template
grep -c "Read .*\.claude/rules/universal\.md" workflow/templates/implementation-prompt.md
grep -B2 -A4 "Read .*\.claude/rules/universal\.md" workflow/templates/implementation-prompt.md | grep -E "(binding|treat|apply)" | head -3

# Review prompt template
grep -c "Read .*\.claude/rules/universal\.md" workflow/templates/review-prompt.md
grep -B2 -A4 "Read .*\.claude/rules/universal\.md" workflow/templates/review-prompt.md | grep -E "(binding|treat|apply)" | head -3
```

**Expected:** Both templates contain a Pre-Flight step with imperative wording binding the reader to the rules file. Match count ≥ 1 per template.

**Violation:** Either template missing the keystone, OR phrasing is advisory ("you may," "consider," "if helpful"). Triggers escalation criterion B1. **Highest-leverage edit in the sprint**; this check is non-negotiable on every session's review.

---

### R7. Bootstrap routing for new protocols + templates present

**Verify (run starting Session 3, 4, 5):**

After Session 3:
```bash
grep -E "(Campaign Orchestration|Campaign Absorption|Campaign Close)" workflow/bootstrap-index.md
grep "campaign-orchestration\.md" workflow/bootstrap-index.md
```

After Session 4:
```bash
grep -E "Operational Debrief" workflow/bootstrap-index.md
grep "operational-debrief\.md" workflow/bootstrap-index.md
```

After Session 5:
```bash
grep "stage-flow\.md\|scoping-session-prompt\.md" workflow/bootstrap-index.md
```

**Expected:** Each new file has at least one match in the "Conversation Type → What to Read" section AND at least one match in the relevant Index table (Protocol Index for protocols; Template Index for templates).

**Violation:** New file committed without bootstrap routing entry. Triggers escalation criterion B2. **Auto-effect-defining check** — without routing, the new file is a sit-there doc.

---

### R8. Workflow-version headers monotonic + correct

**Verify (run at every session's review):**
```bash
for f in workflow/claude/rules/universal.md \
         workflow/claude/skills/close-out.md \
         workflow/templates/implementation-prompt.md \
         workflow/templates/review-prompt.md \
         workflow/templates/work-journal-closeout.md \
         workflow/templates/doc-sync-automation-prompt.md \
         workflow/protocols/codebase-health-audit.md \
         workflow/protocols/impromptu-triage.md \
         workflow/protocols/sprint-planning.md \
         workflow/protocols/campaign-orchestration.md \
         workflow/protocols/operational-debrief.md \
         workflow/templates/stage-flow.md \
         workflow/templates/scoping-session-prompt.md; do
    if [ -f "$f" ]; then
        pre=$(git show <pre-sprint-sha>:$f 2>/dev/null | grep "workflow-version" | head -1)
        post=$(grep "workflow-version" "$f" | head -1)
        echo "$f: pre=[$pre] post=[$post]"
    fi
done
```

**Expected:**
- `claude/rules/universal.md`: 1.0 → 1.1
- `claude/skills/close-out.md`: minor bump (e.g., 1.0.0 → 1.1.0)
- `templates/implementation-prompt.md`: 1.2.0 → 1.3.0
- `templates/review-prompt.md`: 1.1.0 → 1.2.0
- `templates/work-journal-closeout.md`: minor bump
- `templates/doc-sync-automation-prompt.md`: minor bump
- `protocols/codebase-health-audit.md`: 1.0.0 → **2.0.0** (major bump — Phase 2/3 expansion)
- `protocols/impromptu-triage.md`: minor bump (e.g., 1.1.0 → 1.2.0)
- `protocols/sprint-planning.md`: minor bump if cross-reference adds non-trivial content; otherwise patch
- New files: `1.0.0`

**Violation:** Any version bumped downward, OR `codebase-health-audit.md` not at 2.0.0 by Session 6 close-out, OR new file missing version header. Triggers escalation criterion C1.

---

### R9. New file headers complete (workflow-version + last-updated)

**Verify (after each new file's creating session):**
```bash
for f in workflow/protocols/campaign-orchestration.md \
         workflow/protocols/operational-debrief.md \
         workflow/templates/stage-flow.md \
         workflow/templates/scoping-session-prompt.md; do
    if [ -f "$f" ]; then
        head -3 "$f"
    fi
done
```

**Expected:** Each new file's first 3 lines contain:
```
<!-- workflow-version: 1.0.0 -->
<!-- last-updated: 2026-04-26 -->
```
followed by the H1 title.

**Violation:** Missing or malformed header. Tier 2 catches in CONCERNS (auto-fix in-session).

---

### R10. Symlink targets continue to resolve

**Verify (judgmental — run after Session 1 + Session 2):**
The synthesis sprint does not move, rename, or delete any file in `workflow/claude/rules/`, `workflow/claude/skills/`, or `workflow/claude/agents/`. Existing project-side symlinks pointing at these paths continue to resolve.

```bash
ls workflow/claude/rules/universal.md
ls workflow/claude/skills/close-out.md workflow/claude/skills/review.md workflow/claude/skills/diagnostic.md workflow/claude/skills/canary-test.md workflow/claude/skills/doc-sync.md
```

**Expected:** All paths exist as files (no move/rename/delete).

**Violation:** Any of these files renamed or moved. Triggers escalation per spec-by-contradiction §"Do NOT add" / "Do NOT refactor."

---

## Section 3: Quality Invariants

These verify content quality across the sprint (origin footnotes, generalized terminology, cross-reference integrity).

### R11. Every metarepo addition has an Origin footnote

**Verify (run at every session's review):**
```bash
# Count Origin footnotes citing this synthesis sprint or its source notes
grep -rn "Origin:.*synthesis-2026-04-26\|Origin:.*2026-04-21.*evolution\|Origin:.*P26\|Origin:.*P27\|Origin:.*P28\|Origin:.*P29\|Origin:.*P30\|Origin:.*P31\|Origin:.*P32\|Origin:.*P33\|Origin:.*P34" workflow/
```

**Expected:** At least one Origin footnote per substantive new section. The disposition matrix in Phase A enumerated ~25 distinct codifications; expect ~25–35 Origin footnotes total across the sprint's diff (some additions consolidate multiple inputs in one footnote).

**Violation:** A new section, RULE, or protocol exists without an Origin footnote. Tier 2 CONCERNS (in-session fix); becomes ESCALATE if multiple new sections lack footnotes (suggests a systemic miss).

---

### R12. F1–F10 generalized-terminology coverage

**Verify (run at every session's review starting Session 3):**

For each session that creates or modifies content involving the F1–F10 findings:
```bash
# F1: "Work Journal conversation" → "campaign coordination surface"
grep -c "Work Journal conversation" <files-modified-in-session>  # Existing reference is OK only in templates/work-journal-closeout.md context; new content should use generalized term

# F2: recurring-event-driven framing in operational-debrief.md
grep -E "(periodic|event-driven|recurring)" workflow/protocols/operational-debrief.md  # Expect ≥3 matches

# F3: "execution-anchor commit" not "boot commit"
grep -c "boot commit\|execution-anchor commit" workflow/protocols/operational-debrief.md  # New protocol uses execution-anchor; "boot commit" appears only as the ARGUS-specific example

# F4: tiered hot-files
grep -E "(recent-bug|recent-churn|post-incident|maintained.list|code-ownership)" workflow/protocols/codebase-health-audit.md  # Expect ≥5 matches in Phase 2

# F5: 3 non-trading examples for fingerprint pattern
grep -B2 -A10 "fingerprint-before-behavior-change\|fingerprint.before.behavior" workflow/protocols/codebase-health-audit.md | grep -E "(pricing|invoice|A/B|cohort|model.version|recommendation)" | head -5  # Expect references to non-trading scenarios

# F6: generalized absorption axes (no "audit-execution-state" verbatim — should be more general)
grep -B2 -A2 "absorption.axis\|absorption.dimension\|axes" workflow/protocols/campaign-orchestration.md  # Should reference work-execution-state generally

# F7: stage-flow has 3 formats
grep -E "(ASCII|Mermaid|ordered.list)" workflow/templates/stage-flow.md  # Expect all 3

# F8: closed-item terminology in Phase 1 spot check
grep -B2 -A4 "DEF Health Spot.Check\|spot.check" workflow/protocols/codebase-health-audit.md | grep -E "(closed-item|equivalent|Linear|GitHub)"  # Expect generalized terminology

# F9: squash-merge caveat
grep -B2 -A4 "git.commit.body\|state.oracle" workflow/protocols/codebase-health-audit.md | grep -E "(squash|PR|GitHub Action)"  # Expect caveat

# F10: 7-point-check appendix conditional framing
grep -B2 -A4 "7-point\|seven-point\|tracking conversation" workflow/protocols/campaign-orchestration.md | grep -E "(if.*tracking|when.*coordination|applies.*conversation)"  # Expect conditional framing
```

**Expected:** Each F# has a positive grep result in the appropriate file/section. Session 6 close-out must include a table mapping each F# to its addressing file/section (acceptance gate for Session 6).

**Violation:** Missing F# coverage. Triggers escalation criterion B4 (if Session 6 close-out's mapping is incomplete) or CONCERNS (if Tier 2 catches it before close-out).

---

### R13. Safety-tag taxonomy appears ONLY in rejected-pattern addendum

**Verify (run at every session's review):**
```bash
grep -rE "(safe-during-trading|weekend-only|read-only-no-fix-needed|deferred-to-defs)" workflow/protocols/ workflow/templates/ workflow/claude/skills/ workflow/scripts/
```

**Expected:** Matches appear ONLY in `workflow/protocols/codebase-health-audit.md` Phase 2's `### Anti-pattern (do not reinvent)` addendum, with surrounding context that frames the taxonomy as "empirically overruled," "do not reinvent," etc.

**Violation:** Any match outside the addendum, OR matches inside the addendum without rejection-framing context. Triggers escalation criterion B3.

---

### R14. Cross-references resolve

**Verify (run after Session 5 — when all forward-deps should be resolved):**
```bash
# Session 3's forward-dep on Session 5's output
grep -oE "templates/scoping-session-prompt\.md" workflow/protocols/impromptu-triage.md
ls workflow/templates/scoping-session-prompt.md  # Must exist

# Other cross-references
grep -roE "(protocols/|templates/|claude/skills/|claude/rules/|scripts/)[a-z0-9-]+\.(md|py)" workflow/protocols/campaign-orchestration.md workflow/protocols/operational-debrief.md workflow/templates/stage-flow.md workflow/templates/scoping-session-prompt.md workflow/protocols/codebase-health-audit.md | sort -u | while read ref; do
    if [ ! -f "workflow/$ref" ]; then
        echo "BROKEN REFERENCE: workflow/$ref"
    fi
done
```

**Expected:** Every path-based cross-reference in new content resolves to an actual file in the metarepo.

**Violation:** Broken reference. CONCERNS (in-session fix) unless it's the Session 3 → Session 5 forward-dep failing after Session 5 close-out (then it's ESCALATE per criterion C4).

---

### R15. Bootstrap-index existing entries unchanged

**Verify (run after every session that modifies bootstrap-index.md):**
```bash
git show <pre-sprint-sha>:workflow/bootstrap-index.md > /tmp/bootstrap-pre.md
diff /tmp/bootstrap-pre.md workflow/bootstrap-index.md | grep "^<"
```

**Expected:** Diff's `<` lines (deletions from pre-sprint state) should be empty — only `>` lines (additions) should appear. Existing entries in "Conversation Type → What to Read," Protocol Index, Template Index, and Schema Index are unchanged.

**Violation:** Any existing entry modified. Triggers escalation per spec-by-contradiction "Do NOT refactor" boundary.

---

## Section 4: Process Invariants

These verify the sprint's process discipline (close-outs, version stamps, dependency chain).

### R16. Each session's close-out file present at expected path

**Verify (run during sprint, after each session):**
```bash
ls argus/docs/sprints/synthesis-2026-04-26/session-{0,1,2,3,4,5,6}-closeout.md
```

**Expected:** After Session N closes, file `session-N-closeout.md` exists in the sprint directory, contains structured close-out report (per `claude/skills/close-out.md`), and includes the structured JSON appendix (`json:structured-closeout`).

**Violation:** Missing close-out, OR malformed JSON appendix. Tier 2 CONCERNS unless multiple close-outs missing (then ESCALATE per criterion D2).

---

### R17. Session pre-flight verifies prior session's outputs

**Verify (Session 1+ pre-flight):**
- Session 1 pre-flight: grep for P28/P29 in argus SUMMARY.md → halt if not found (verifies Session 0 landed)
- Session 2 pre-flight: grep for keystone Pre-Flight wiring in implementation-prompt.md → halt if not found (verifies Session 1 landed)
- Session 3 pre-flight: grep for evolution-note synthesis-status headers → halt if not found (verifies Session 2 landed)
- Session 4 pre-flight: ls campaign-orchestration.md → halt if not found
- Session 5 pre-flight: ls operational-debrief.md → halt if not found
- Session 6 pre-flight: ls all 3 new templates + phase-2-validate.py → halt if any not found

**Expected:** Each session pre-flight halts if expected prior-session output is missing.

**Violation:** Pre-flight check missing or skipped. Tier 2 CONCERNS (the implementer should add the check before proceeding); ESCALATE if implementer proceeded past a missing prior output.

---

### R18. No new top-level metarepo directories

**Verify:**
```bash
git diff <pre-sprint-sha>..HEAD --name-status -- workflow/ | awk '$1=="A"' | awk -F'/' '{print $2}' | sort -u
```

**Expected:** All new files appear under existing directories (`protocols/`, `templates/`, `claude/`, `runner/`, `schemas/`, `scripts/`, `scaffold/`, `evolution-notes/`). No new top-level subdirectories.

**Violation:** New top-level directory introduced. Triggers escalation per spec-by-contradiction §"Do NOT add."

---

### R19. No new dependencies introduced

**Verify (after Session 5 — the only Python addition):**
```bash
head -20 workflow/scripts/phase-2-validate.py
grep -E "^(import|from)" workflow/scripts/phase-2-validate.py | sort -u
```

**Expected:** Only stdlib imports. Specifically the `csv` module + maybe `sys`, `argparse`, `pathlib`. Nothing from PyPI.

**Violation:** Non-stdlib import. Tier 2 CONCERNS (rewrite in stdlib) or ESCALATE if a PyPI dep is judged unavoidable (operator decides whether to introduce it).

---

### R20. Argus runtime untouched throughout (continuous verification)

This is R4 restated as a continuous check: runs at every session's Tier 2 review, not just the session that creates the most risk. The grep is cheap; the regression mode (a Session 3 commit accidentally drifting into argus runtime) is real.

**Verify (every session):**
```bash
git diff <pre-sprint-sha>..HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/
```

**Expected:** Empty. Permanently. Until sprint completion.

**Violation:** Same as R4. Hard escalation per A1.

---

## Tier 2 Reviewer Workflow

For each session's Tier 2 review:

1. **Run R1, R2, R5, R10, R20** unconditionally (sealed-content + structural integrity, cheap to verify).
2. **Run R3** after Session 2.
3. **Run R6** after Session 1 + every subsequent session (keystone wiring is the highest-leverage check).
4. **Run R7** after Sessions 3, 4, 5 (per their respective bootstrap entries).
5. **Run R8** after every session that bumps a version.
6. **Run R9** after Sessions 3, 4, 5 (new files only).
7. **Run R11, R12, R13** at every session's review starting from when relevant content lands.
8. **Run R14** after Session 5 (forward-dep resolution).
9. **Run R15** after every session that touches bootstrap-index.md.
10. **Run R16, R17, R18, R19** at the relevant session's review.

The Tier 2 review prompt (Phase D artifact) embeds these checks per session; the @reviewer subagent runs them as part of the structured-verdict generation.

If ANY check produces a violation:
- Cross-reference against escalation-criteria.md to determine ESCALATE vs CONCERNS.
- For CONCERNS: implementer fixes in-session via post-review-fix loop.
- For ESCALATE: stop the sprint, route to operator.

---

## Coverage Summary

| Risk surfaced in spec | Regression check | Detection layer |
|---|---|---|
| RETRO-FOLD content semantic regression | R1, R2 | Mechanical diff |
| Evolution-note body modification | R3 | Mechanical diff |
| ARGUS runtime modified | R4, R20 | Mechanical path filter |
| Keystone wiring miss | R6 | Mechanical grep + imperative-phrasing check |
| Bootstrap routing miss | R7 | Mechanical grep on bootstrap-index |
| Workflow-version regression | R8 | Mechanical version comparison |
| F1–F10 finding not addressed | R12 | Mechanical grep per F# + Session 6 close-out mapping |
| Safety-tag taxonomy reintroduction | R13 | Mechanical grep with framing-context check |
| Cross-reference broken | R14 | Mechanical file-existence check |
| Origin footnote missing | R11 | Mechanical grep count |
| Compaction-driven regression | (See escalation C3) | Tier 2 judgment |
| Symlink target moved | R10 | Mechanical file-existence check |
| New file lacks version header | R9 | Mechanical head + grep |
| New top-level directory | R18 | Mechanical diff path analysis |
| New PyPI dependency | R19 | Mechanical import scan |

The 9 risks from spec §Relevant Risks all have at least one regression check. Compaction risk (the one judgment-based item) is handled via the Tier 2 reviewer's structured-verdict process per escalation criterion C3, not via this checklist.

---

## Embedded Document 4: Sprint-Level Escalation Criteria

The full Sprint-Level Escalation Criteria for synthesis-2026-04-26 follows. It defines the conditions that MUST produce an ESCALATE verdict from the Tier 2 reviewer rather than CONCERNS or CLEAR.

# Sprint synthesis-2026-04-26: Sprint-Level Escalation Criteria

> Tier 2 reviewer (the @reviewer subagent invoked at session close) decides whether a session's verdict is **CLEAR**, **CONCERNS**, or **ESCALATE**. This document defines the conditions under which the verdict MUST be ESCALATE rather than CONCERNS.
>
> Escalation routes the issue to operator (Steven) for judgment rather than allowing in-session auto-fix. Use ESCALATE when the failure mode is structural (touches sealed content, defeats the sprint's purpose, violates a hard kickoff constraint) — not for surface-level quality issues that can be resolved within the session via the @reviewer's CONCERNS feedback loop.

---

## Escalation Triggers — must produce ESCALATE verdict

### Category A: Hard constraint violations (kickoff-mandated)

#### A1. ARGUS runtime code, tests, or configuration modified

**Detection:** Any commit in this sprint touches a path under `argus/argus/`, `argus/tests/`, `argus/config/`, or `argus/scripts/`.

**Verification:**
```bash
git log <session-start-sha>..HEAD -- argus/argus/ argus/tests/ argus/config/ argus/scripts/
```
Should return empty. Non-empty result is an immediate escalation.

**Why escalate:** The kickoff explicitly excluded ARGUS runtime work from this sprint. The constraint is operator-set, not @reviewer-overridable. Even if the change "looks safe," it requires operator judgment about whether to absorb it (extending sprint scope) or revert it.

**Operator action after escalation:** Decide whether to: (a) revert the change in a fix commit, (b) extend the sprint scope to include the change with explicit acceptance and updated regression tests, or (c) split the change into a separate ARGUS-side impromptu sprint.

---

#### A2. Evolution-note body modified

**Detection:** `git diff <session-start-sha>..HEAD -- workflow/evolution-notes/2026-04-21-*.md` shows changes to lines below the metadata block (the body content).

**Verification:** For each evolution note, the diff must contain ONLY the additive `**Synthesis status:**` line in the metadata block. Any change to a body line — including whitespace-only changes, typo "fixes," or Markdown formatting normalizations — escalates.

**Why escalate:** The 3 evolution notes are the audit trail. The kickoff explicitly preserves their bodies. If the @reviewer detects body changes, the session's diff cannot be safely landed without operator review.

**Operator action:** Verify whether the body change was accidental (revert) or intentional (operator decides whether the audit-trail-modification cost is justified).

---

#### A3. RETRO-FOLD content semantically regressed

**Detection:** `git diff <session-start-sha>..HEAD -- workflow/claude/rules/universal.md` shows changes to RULE-038 through RULE-050 bodies that are not the explicitly-permitted RULE-038 5th sub-bullet addition.

**Verification:**
- Pre-sprint state: RULE-038 has 4 sub-bullets; RULEs 039–050 are byte-for-byte preserved.
- Post-Session-1 state: RULE-038 has 5 sub-bullets (the new sub-bullet is the only addition); RULEs 039–050 are byte-for-byte unchanged; new RULEs 051–053 appended in new sections after RULE-050.
- Post-Sessions-2–6: same as post-Session-1 for the universal.md content.

**Why escalate:** RETRO-FOLD's P1–P25 synthesis is sealed by `RETRO-FOLD-closeout.md` and metarepo commit `63be1b6`. The kickoff explicitly forbids re-derivation. Any semantic change requires operator authorization.

**Operator action:** Verify whether the change is a wording fix (low-stakes; operator may approve in-place), a semantic change (escalates further to "should we open a strategic check-in to revisit RETRO-FOLD?"), or accidental (revert).

---

### Category B: Sprint-level structural failures

#### B1. Keystone Pre-Flight wiring missing or advisory

**Detection:** After Session 1 close-out, `templates/implementation-prompt.md` Pre-Flight Checks section does NOT contain a step explicitly reading `.claude/rules/universal.md`, OR the step's wording is advisory ("you may," "consider," "if helpful") rather than imperative ("read," "treat as binding for this session").

**Verification:**
```bash
grep -A5 "Pre-Flight Checks" workflow/templates/implementation-prompt.md | grep -E "(read .claude/rules/universal\.md|.claude/rules/universal\.md.*binding)"
```
Must return ≥ 1 line with imperative phrasing. Same check for `templates/review-prompt.md`.

**Why escalate:** The keystone Pre-Flight wiring is the single highest-leverage edit in the sprint. Without it, RETRO-FOLD's P1–P25 RULE coverage remains weakly wired (only RULE-039 is inline-cited from a template) and every new RULE in this sprint has the same problem. Missing or advisory phrasing is sprint failure.

**Operator action:** Verify the keystone is present + imperative; if missing, Session 1 must be redone (cannot proceed to Session 2+ without it stable).

---

#### B2. Bootstrap routing miss

**Detection:** A new protocol file (`campaign-orchestration.md` or `operational-debrief.md`) is committed but `bootstrap-index.md` does not have:
- A "Conversation Type → What to Read" entry pointing at the new protocol, AND
- A row in the Protocol Index table

OR a new template file (`stage-flow.md` or `scoping-session-prompt.md`) is committed but `bootstrap-index.md` Template Index does not have a row for it.

**Verification:**
- After Session 3: `grep -i "campaign.orchestration\|campaign.absorption" workflow/bootstrap-index.md` must return matches in BOTH the "Conversation Type → What to Read" section AND the Protocol Index table.
- After Session 4: same for `operational-debrief`.
- After Session 5: `grep "stage-flow\|scoping-session" workflow/bootstrap-index.md` must return matches in the Template Index table.

**Why escalate:** A new protocol without a routing entry is a sit-there doc — exactly the failure mode this sprint is designed to prevent. Per the auto-effect principle (Phase A pushback round 1), unrouted protocols defeat the sprint's purpose.

**Operator action:** Add the missing routing entry as a follow-on commit in the same session, OR escalate to a separate "bootstrap-index sweep" session if multiple entries are missing.

---

#### B3. Safety-tag taxonomy reintroduced

**Detection:** Any new metarepo content (in any session, any file) contains a 4-tag safety taxonomy (`safe-during-trading` / `weekend-only` / `read-only-no-fix-needed` / `deferred-to-defs`) or its core+modifier expansion as a *recommended* mechanism — rather than as a *rejected pattern* documented in `codebase-health-audit.md` Phase 2's `### Anti-pattern (do not reinvent)` addendum.

**Verification:** For each session, search the new content:
```bash
grep -E "(safe-during-trading|weekend-only|read-only-no-fix-needed|deferred-to-defs)" workflow/protocols/*.md workflow/templates/*.md workflow/claude/skills/*.md workflow/scripts/*.py
```
Acceptable matches: ONLY in the rejected-pattern addendum section of `codebase-health-audit.md` Phase 2 (with explicit framing: "do not reinvent," "empirically overruled," etc.). Any other location is escalation.

**Why escalate:** The safety-tag rejection was an explicit operator decision in Phase A pushback round 2, based on Sprint 31.9 execution evidence. Reintroduction would silently undo that decision and propagate a pattern that didn't earn its load-bearing role.

**Operator action:** Remove the reintroduced content; verify the rejected-pattern addendum is correctly framed; if the reintroduction was the @reviewer noticing an "obvious gap," escalate further to operator review of whether the rejection should actually be revisited (very unlikely outcome but theoretically possible).

---

#### B4. F1–F10 finding not addressed

**Detection:** Session 6 close-out does NOT enumerate which file/section addresses each F# finding from the synthetic-stakeholder pass, OR a Tier 2 review of any session detects ARGUS-specific terminology in new metarepo content that is not contextually framed (e.g., "trading session" used universally, "DEF" used universally, "Work Journal conversation" used universally without "or equivalent coordination surface").

**Verification:**
- Session 6 close-out must contain a table mapping F1–F10 to their addressing file/section.
- Session 6 Tier 2 review must include a focus item: "verify generalized terminology coverage."
- Any session's diff that introduces new ARGUS-specific terminology without contextual framing escalates.

**Why escalate:** The F1–F10 findings were first-class deliverables (deliverable 14 in the sprint spec). Missing coverage means the synthetic-stakeholder pass was wasted work and the new protocols ship as ARGUS-specific despite the design intent.

**Operator action:** Verify which F# findings are missed; either fix them in a follow-on commit within Session 6, or split into a "F1–F10 generalized-terminology pass" follow-on session.

---

### Category C: Acceptance/quality failures

#### C1. Workflow-version regression

**Detection:** Any modified file's `<!-- workflow-version: X.Y.Z -->` header is bumped DOWNWARD, OR `protocols/codebase-health-audit.md` is modified in Session 6 but not bumped to 2.0.0, OR a new file lacks a workflow-version header.

**Verification:**
```bash
for f in $(git diff --name-only <session-start-sha>..HEAD -- workflow/); do
    pre=$(git show <session-start-sha>:$f 2>/dev/null | grep "workflow-version" | head -1)
    post=$(git show HEAD:$f | grep "workflow-version" | head -1)
    echo "$f: pre=$pre post=$post"
done
```
Manually verify each file's version monotonically advances; new files have `1.0.0`.

**Why escalate:** Versions are how downstream consumers detect protocol changes. A regression breaks that signal. `codebase-health-audit.md` specifically must reach 2.0.0 because the Phase 2/3 expansion materially changes the protocol's scope.

**Operator action:** Bump versions correctly in a follow-on commit; verify monotonic advancement.

---

#### C2. `phase-2-validate.py` invocation phrased advisorially

**Detection:** `protocols/codebase-health-audit.md` Phase 2 references `scripts/phase-2-validate.py` but the wording is advisory ("you may run...", "consider running...", "the validator can be run...") rather than imperative gate-language ("Phase 2 cannot complete until phase-2-validate.py exits zero," "before proceeding to Phase 3, run...").

**Verification:**
```bash
grep -B2 -A5 "phase-2-validate" workflow/protocols/codebase-health-audit.md
```
The surrounding wording must be imperative. Advisory phrasing escalates.

**Why escalate:** A validator invoked advisorially is not a gate — it's a suggestion. The whole point of `scripts/phase-2-validate.py` is to make CSV integrity non-bypassable. Advisory phrasing converts a structural defense into operator-memory-dependent guidance, defeating the auto-effect goal.

**Operator action:** Rewrite the wording as imperative; verify by re-grep.

---

#### C3. Compaction-driven regression detected by Tier 2

**Detection:** During Tier 2 review of any session, the @reviewer detects evidence that the implementer's context was compacted mid-session (incomplete edits, contradictory changes within the same file, references to non-existent files, repeated stub content, or any other signal that internal session state was lost). This is distinct from "the implementer made a mistake" — it's specifically the compaction failure mode.

**Verification:** Judgment-based. The @reviewer's review report should explicitly note compaction signals if detected.

**Why escalate:** Compaction-driven regressions can cascade in non-obvious ways. A fresh session is the only reliable remediation. Continuing the same session risks compounding the problem.

**Operator action:** Discard the session's commits; restart the session in a fresh Claude Code conversation with the same prompt + the close-out from the failed attempt as context.

---

#### C4. Forward-dependency unresolved by Session 5 close-out

**Detection:** Session 3's `protocols/impromptu-triage.md` extension references `templates/scoping-session-prompt.md`, which is created in Session 5. After Session 5 close-out, the file path referenced in `impromptu-triage.md` does NOT resolve to an actual file in the repo.

**Verification:**
```bash
grep -oE "templates/scoping-session-prompt\.md" workflow/protocols/impromptu-triage.md
ls workflow/templates/scoping-session-prompt.md
```
Both must succeed.

**Why escalate:** A forward-reference that never resolves is a broken-link bug. Pattern (a) was operator-approved with the understanding that Session 5 closes the loop. If Session 5 fails to close it, the impromptu-triage extension has a dead reference until a follow-on commit lands.

**Operator action:** Either create the missing file (if Session 5's scope was incomplete) or redact the reference from impromptu-triage.md (if the scope was correctly Session 5 but the file got dropped).

---

### Category D: Process failures

#### D1. Session 0 not landed before Session 1 begins

**Detection:** Session 1 implementation prompt is invoked, but `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` does not contain P28+P29 entries.

**Verification:** Session 1 pre-flight should grep for P28/P29 in SUMMARY.md and halt if not found.

**Why escalate:** Session 1+ reference the synthesis input set as stable. If P28+P29 aren't in SUMMARY.md, the inputs are not stable; metarepo work would land citing artifacts that don't yet exist on the argus side.

**Operator action:** Halt Session 1; complete Session 0 first; then resume.

---

#### D2. Tier 2 reviewer cannot determine acceptance gate state

**Detection:** A session's close-out claims COMPLETE but the @reviewer cannot verify acceptance gates (e.g., the close-out doesn't include the grep results, the diff is malformed, the close-out is missing).

**Verification:** Each session's close-out must contain explicit verification commands + their outputs. Missing or unverifiable outputs escalate.

**Why escalate:** Without verifiable gates, the @reviewer cannot produce a defensible verdict. CONCERNS would be paper-only; ESCALATE forces operator to actually verify.

**Operator action:** Verify each gate manually; produce a corrected close-out; re-run @reviewer.

---

#### D3. Sprint scope creep beyond the 18 OUT items

**Detection:** Any session's diff touches a file or introduces a feature that is explicitly listed in `spec-by-contradiction.md` §"Out of Scope" or §"Do NOT modify."

**Verification:** Each Tier 2 review must include a "scope-boundary check": cross-reference the diff against the OUT list. Any match escalates.

**Why escalate:** Scope discipline is operator-set in spec-by-contradiction. Even seemingly-helpful additions (e.g., "while I was here, I cleaned up the heading hierarchy in `codebase-health-audit.md`") require operator authorization. The kickoff explicitly excluded restructurings, and the spec listed 18 OUT items deliberately.

**Operator action:** Either revert the out-of-scope change or extend the sprint scope explicitly with updated regression tests and an addendum to the spec.

---

## What does NOT escalate (Tier 2 resolves via CONCERNS)

The following are CONCERNS-level issues. The @reviewer notes them in the review report; the implementer fixes them within the same session via the post-review-fix loop:

- **Markdown formatting inconsistencies** (table alignment, heading-level drift within a section, inline-code vs fenced-code style). Minor cosmetic; fix in-session.
- **Origin footnote wording variance** (citing "Sprint 31.9 retro" vs "synthesis-2026-04-26 evolution note 1" — both are acceptable as long as the citation is unambiguous). Style-level; fix only if ambiguous.
- **Cross-reference path typos** (linking to `protocols/campaign-orhestration.md` instead of `campaign-orchestration.md`). Fixable; flag in CONCERNS.
- **Missing one example in a multi-example section** (e.g., the fingerprint pattern has 2 non-trading examples instead of the F5-required 3). CONCERNS unless ALL non-trading examples are missing (which would be an F5 failure → escalates per B4).
- **Imprecise wording** ("the operator should..." vs "the operator must...") that doesn't change semantic intent. Style.
- **Section ordering within a new file** (e.g., placing the appendix before the decision matrix). Re-order in CONCERNS.
- **Workflow-version bump correctness when ambiguous** (e.g., is `templates/implementation-prompt.md` getting a 1.2.0 → 1.2.1 patch bump or 1.2.0 → 1.3.0 minor bump?). Tier 2 picks the conservative interpretation and notes it; operator can override later.
- **Test-count delta in close-outs that don't apply** (the metarepo has no test suite; close-outs that include test-count fields can leave them as `N/A` rather than escalating).

These are all in-session fixable. The @reviewer's CONCERNS verdict triggers the post-review-fix loop in the implementer's same session per `templates/implementation-prompt.md` §"Post-Review Fix Documentation."

---

## Tier 3 review handling

If any Category A or B trigger fires, the failure mode is structural enough to warrant a **Tier 3 architectural review** in addition to operator escalation. Tier 3 review (`protocols/tier-3-review.md`) examines whether the failure indicates a flaw in the sprint design itself (e.g., the keystone wiring concept was wrong) versus a pure execution error (e.g., the implementer dropped the keystone step).

Tier 3 should be invoked if:
- B1 fires AND the implementation prompt was structurally defective (the keystone instruction was unclear or misplaced)
- B2 fires for 2+ sessions consecutively (suggests bootstrap routing pattern itself is hard to follow)
- A3 fires (RETRO-FOLD content regression at any scope; the sealed-content boundary was crossed; needs structural review of how RETRO-FOLD is protected)

For all other escalations, operator review without Tier 3 is sufficient.

---

## Escalation Procedure

1. **@reviewer subagent produces ESCALATE verdict** in its structured JSON appendix:
   ```json
   {
     "verdict": "ESCALATE",
     "escalation_triggers": ["A1" | "A2" | ... | "D3"],
     "findings": [{ "severity": "CRITICAL", "category": "...", ... }]
   }
   ```
2. **The session's close-out is preserved.** Do NOT amend the close-out to "fix" the escalation in the same session — escalation means operator review is required.
3. **Operator (Steven) reads the review report + close-out** in the work journal conversation.
4. **Operator decides:** revert / fix-in-place / extend-scope / split-to-followon-session / accept-with-rationale.
5. **Decision logged** as a DEC entry (this sprint reserves no new DEC numbers, so any escalation-driven decision is logged in the sprint close-out's "judgment calls" section + a follow-on DEC if the decision has cross-sprint implications).
6. **If accepted:** sprint continues. **If reverted/redone:** the affected session re-runs from scratch.

The work journal handoff prompt (Phase D artifact) explicitly instructs the operator on this procedure so escalations don't surprise the workflow.

---

## End of Review Context

The four embedded documents above are the complete review contract. The Tier 2 reviewer should be able to:

1. Read this entire file
2. Read the session's close-out report
3. Run `git diff HEAD~1` (or appropriate range) to see the diff
4. Run `.claude/rules/universal.md` for universal-rule context
5. Run the regression checks specified for this session per §4 of the embedded Regression Checklist
6. Cross-reference any concerns against the embedded Escalation Criteria
7. Produce a structured-verdict review report

If at any point the reviewer needs additional context not embedded in this file, that's a signal that the planning artifacts are incomplete — flag it as a finding in the review report.
