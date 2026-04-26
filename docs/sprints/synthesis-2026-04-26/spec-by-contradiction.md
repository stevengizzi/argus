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
