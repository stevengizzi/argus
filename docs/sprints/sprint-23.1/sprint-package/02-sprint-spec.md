# Sprint 23.1: Autonomous Runner Protocol Integration

## Goal
Integrate all autonomous sprint runner documentation — protocols, schemas,
templates, guides, and decision log entries — into the ARGUS repository, and
update existing skill files, agent files, and reference documents to support
dual-mode (autonomous + human-in-the-loop) sprint execution. This sprint
produces no code changes; it is documentation-only.

## Scope

### Deliverables
1. 15 new documentation files placed in their final repo locations under
   `docs/protocols/`, `docs/protocols/schemas/`, `docs/protocols/templates/`,
   and `docs/guides/`
2. `.claude/skills/close-out.md` extended with structured JSON appendix section
3. `.claude/skills/review.md` updated with CONCERNS verdict in prose template
   AND structured JSON verdict section appended
4. `.claude/agents/reviewer.md` updated with CONCERNS verdict support
5. `docs/project-knowledge.md` updated with runner subsection in Workflow
6. `docs/architecture.md` updated with runner component and file structure
7. `docs/decision-log.md` updated with DEC-278 through DEC-297 (20 entries)
8. `docs/dec-index.md` updated with 20 new DEC entries
9. `docs/sprint-history.md` updated with Sprint 23.1 entry

### Acceptance Criteria
1. All 15 new files exist at correct paths (5 protocol + 4 schema + 4 template + 2 guide)
2. close-out.md has "Structured Close-Out Appendix" section with JSON schema and rules
3. review.md Step 2 has CONCERNS verdict determination criteria
4. review.md Step 3 shows `[CLEAR | CONCERNS | ESCALATE]`
5. review.md has "Structured Review Verdict" section at end
6. reviewer.md Output section lists CLEAR/CONCERNS/ESCALATE
7. project-knowledge.md Workflow section references three-tier architecture and runner
8. architecture.md has Sprint Runner component and updated file structure
9. decision-log.md contains DEC-278 through DEC-297 with no numbering gaps
10. dec-index.md has all 20 new entries
11. sprint-history.md has Sprint 23.1 entry
12. All existing tests pass unchanged (pytest + vitest)

### Performance Benchmarks
N/A — documentation-only sprint.

### Config Changes
No config changes in this sprint.

## Dependencies
- 17 source files committed to `docs/sprints/sprint-23.1/source/` before
  Session 1 begins (developer pre-flight step)
- DEC-277 is the current max DEC number
- Sprint 23 / 23.05 must be complete

## Relevant Decisions
- DEC-275: Compaction risk scoring system (informs session sizing)

## Relevant Risks
- No active risks apply to a documentation-only sprint

## Session Count Estimate
2 sessions estimated. Content is pre-written; Claude Code is placing files
and making targeted edits, not generating novel content.
