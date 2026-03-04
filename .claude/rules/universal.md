# Universal Rules - Cross-Project Rule Library
# Loaded into .claude/rules/ for every project.
# Source: Empirical patterns from ARGUS (65 convos, 21 sprints), MuseFlow (11 convos, 4 sprints), Grove (11 convos, 6 phases).
# Version: 1.0

---

## 1. Prompt Adherence

RULE-001: Execute exactly what the implementation prompt specifies. Do not add features, refactor adjacent code, or "improve" things outside the stated scope. If the prompt says "modify function Y in file X," that is the boundary.

RULE-002: If current code behavior appears to conflict with the prompt intent, flag it -- do not rationalize it as "intended design." (Grove: Claude Code rationalized a broken save button as intended; it was a bug. This pattern recurred across projects.)

RULE-003: Read every file listed in the prompt file-read section before writing any code. Do not infer interfaces from memory or assumptions. (ARGUS: "Read these files first, then implement" was the single most reliable prompt pattern.)

RULE-004: Respect all "do not modify" and "do not break" constraints explicitly. If the prompt lists files or behaviors to preserve, treat violations as blocking errors, not warnings. (Grove: An audio analysis session clobbered a FLAC artwork fix because no boundary was set; after boundaries were added, regressions dropped to near zero.)

RULE-005: When the prompt includes a "Definition of Done" or gate-check section, complete every item before considering the session finished. Do not self-assess as complete if any verification step is untested.

---

## 2. Scope Discipline

RULE-006: One session, one objective. If a task has multiple independent concerns, they should be separate sessions. Do not combine unrelated fixes into a single session. (Grove: Every task that completed cleanly had a single well-defined objective. Every task that sprawled started with too broad a scope.)

RULE-007: If you discover a bug or improvement opportunity outside your current scope, document it in the close-out report under "Deferred Items" -- do not fix it now. Scope expansion mid-session is the primary driver of regressions. (ARGUS: Sprint sub-numbering emerged because scope-expanded sessions created review chaos.)

RULE-008: If the first approach to a problem fails, do not attempt more than one additional approach in the same session without explicit user approval. Uncontrolled retries compound context consumption and increase regression risk.

RULE-009: For prompts that list multiple tasks (e.g., "fix bugs A, B, C"), complete and verify each task fully before starting the next. Do not interleave work across tasks.

---

## 3. Review Compliance

RULE-010: Never skip the close-out protocol. It is the final act of every implementation session. Complete the full structured report: change manifest, judgment calls, scope verification, regression checks, test results, self-assessment (CLEAN / MINOR_DEVIATIONS / FLAGGED).

RULE-011: Self-assessment must be honest. If you deviated from spec, mark MINOR_DEVIATIONS or FLAGGED and explain what changed and why. Do not mark CLEAN if any scope item was skipped, modified, or reinterpreted. (Cross-project: rationalization of deviations as "improvements" was the most common review failure.)

RULE-012: If the Tier 2 review prompt is provided, do not modify it. The review prompt was pre-generated during sprint planning to match the implementation spec. Altering it defeats the purpose of independent review.

RULE-013: During Tier 2 review (reviewer agent or fresh session), operate in read-only mode. Analyze the diff, compare to spec, produce a verdict. Do not fix anything -- only report.

---

## 4. Documentation Integrity

RULE-014: When the implementation prompt includes a doc-update checklist, complete all doc updates in the same session as the code changes. Do not defer documentation to a later session. (MuseFlow: doc sync consumed ~15-20% of Claude.ai conversation time because updates were batched rather than immediate. Grove: 5 days of deferred updates produced duplicate DEC numbers and stale descriptions across documents.)

RULE-015: When adding a decision log entry, verify the current highest DEC number in the log before assigning a new one. Do not assume or guess the next number. Duplicate DEC numbers create cross-reference failures.

RULE-016: When updating one document that references content in other documents (e.g., import pipeline order, architecture decisions), verify that all related documents are consistent. If you update the pipeline order in architecture.md, check that CLAUDE.md and the sprint plan reflect the same order.

RULE-017: Decision log entries must include: the decision, the rationale, alternatives considered (if any), and the scope of impact. A DEC entry that only states "we decided X" without rationale is incomplete.

RULE-018: Do not modify Project Knowledge files or Claude.ai-managed documents from Claude Code unless explicitly instructed. The source of truth for planning-layer docs is Claude.ai; Claude Code owns code and code-adjacent docs (.claude/*, README, inline docs).

---

## 5. Codebase Hygiene

RULE-019: Every implementation session must end with all tests passing. If a new test fails, fix it before closing out. If an existing test breaks, that is a regression -- flag it in the close-out report, do not delete or skip the test.

RULE-020: When the prompt specifies a target test count (e.g., "should end at ~X tests"), verify the actual count before closing out. Report the delta if it differs.

RULE-021: Use explicit, descriptive names for all new functions, variables, classes, and files. Follow the project existing naming conventions. If no convention exists, prefer verbose clarity over brevity.

RULE-022: Do not introduce new dependencies without explicit approval in the implementation prompt. If a library would significantly simplify the implementation, flag it in the close-out report as a recommendation -- do not install it.

RULE-023: Commit messages should reference the sprint/session identifier and summarize what changed. Format: [Sprint X / Session Y] Brief description of changes. If the project uses a different commit convention, follow that instead.

RULE-024: When modifying a component that has been the source of prior regressions (check the decision log or risk register), add extra caution: re-run all related tests, verify the specific behaviors listed in "do not break" sections, and flag the component as high-risk in the close-out report. (Grove: RecordingEditPanel.svelte was modified across 8+ sessions and regressed at least twice.)

---

## 6. Compaction Defense

RULE-025: Prefer short, focused sessions over long marathons. If a task is estimated at more than ~45 minutes of active work or touches more than 3 files substantially, it should likely be split into multiple sessions. (Grove: 5-compaction marathon sessions produced more regressions than progress. ARGUS: Sessions exceeding context produced the worst regression rates.)

RULE-026: Front-load file reads. Read all relevant files at the start of the session before making any changes. Do not defer reads to "when needed" -- by the time you need them, earlier context may have been compacted.

RULE-027: If you notice your context becoming large (many files read, many changes made, long conversation history), proactively checkpoint: commit current work, run tests, produce a partial close-out, and suggest continuing in a fresh session. Do not push through -- compaction-induced regressions cost more than the overhead of a session split.

RULE-028: When producing a close-out report, include a "Context State" field: GREEN (session completed well within context limits), YELLOW (session was long, context may be compressed), or RED (session hit compaction, outputs should be verified independently). This gives the review layer a signal about report reliability.

RULE-029: At the start of every session, re-read the implementation prompt in full even if it was provided earlier in the conversation. Do not rely on your summary of it -- the original wording contains constraints that summaries drop.

---

## 7. Diagnostic Protocol

RULE-030: After two failed attempts to fix the same bug, stop attempting fixes. Switch to diagnostic-first mode: build a standalone test or script that reproduces the bug in isolation, outside the application code. Only after the root cause is confirmed should you modify application code. (Grove DEC-022: diagnostic-first had 100% success rate vs. ~33% for ad-hoc fixes. This pattern held across all three projects.)

RULE-031: When entering diagnostic mode, document what was already tried and why it failed before designing the diagnostic test. This prevents the diagnostic from re-testing approaches already known to fail. (Grove: FLAC artwork saga consumed 6+ iterations because each session did not know what previous sessions had tried.)

RULE-032: The diagnostic test must be minimal -- isolate the exact behavior under investigation. Do not build a comprehensive test suite at this stage. The goal is a binary signal: does the API/function/behavior work as expected, yes or no?

RULE-033: After a successful diagnostic leads to a fix, add a regression test for the specific failure mode before closing out the session. The regression test ensures the bug cannot silently return.

---

## 8. Research and Infrastructure

RULE-034: Do not build on provisional infrastructure. If the implementation depends on an external service, library, or data source that has not been validated for the project actual requirements, flag this as a blocker. (ARGUS: Building 10 sprints on Alpaca before discovering Databento was the right choice wasted significant effort.)

RULE-035: If the implementation prompt references an API, service, or library you have not used before in this project, read its documentation or source before implementing against it. Do not guess at interfaces.

RULE-036: When performance is relevant (data processing, API calls, rendering), include performance benchmarks in your verification. "It works" is insufficient if it takes 100x longer than acceptable. (ARGUS Sprint 8: VectorBT implementation used iterrows() and took 4+ hours; the spec had not included performance gates.)

---

## Meta

This file is maintained in the metarepo and seeded into every project during bootstrap.
Project-specific rules go in separate files in the same .claude/rules/ directory (e.g., backtesting.md for ARGUS-specific rules).
Do not modify this file from within a project -- changes flow from metarepo to projects, not the reverse.
To propose a new universal rule, flag it in the close-out report and it will be evaluated during the next strategic check-in.
