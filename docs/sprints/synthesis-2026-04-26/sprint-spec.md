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
