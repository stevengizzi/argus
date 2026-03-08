# Sprint 23.1 Design Summary

**Sprint Goal:** Integrate all autonomous runner documentation into the ARGUS repo and update existing files to support dual-mode (autonomous + human-in-the-loop) sprint execution.

**Session Breakdown:**
- Session 1: Create all new documentation files from staging directory
  - Creates: 15 files across `docs/protocols/`, `docs/protocols/schemas/`, `docs/protocols/templates/`, `docs/guides/`
  - Modifies: None
  - Integrates: N/A (documentation only)
- Session 2: Modify existing repo files — skills, agent, reference docs, DEC entries
  - Creates: None
  - Modifies: `.claude/skills/close-out.md`, `.claude/skills/review.md`, `.claude/agents/reviewer.md`, `docs/project-knowledge.md`, `docs/architecture.md`, `docs/decision-log.md`, `docs/dec-index.md`, `docs/sprint-history.md`
  - Integrates: References new files created in S1

**Key Decisions:**
- New files staged at `docs/sprints/sprint-23.1/source/` before Claude Code sessions begin (developer pre-flight step)
- Source files are pre-renumbered (DEC-278 through DEC-297); no renumbering step in S1
- DEC entries cover DEC-278 through DEC-297 (20 entries total: 13 original runner + 7 enhancements)
- CONCERNS verdict added to review skill prose AND structured output (not just structured)
- Reviewer agent updated alongside review skill for consistency
- Claude.ai project instruction file updates are manual post-sprint

**Scope Boundaries:**
- IN: Creating new documentation files, modifying existing docs, adding DEC entries
- OUT: Building sprint-runner.py (Sprint 23.5), modifying source code/tests, config changes

**Regression Invariants:**
- All existing tests must still pass (no code changes in this sprint)
- No source code files modified
- Existing skill file behavior preserved (new sections are additive; CONCERNS is additive to verdict options)

**File Scope:**
- Modify: `.claude/skills/close-out.md`, `.claude/skills/review.md`, `.claude/agents/reviewer.md`, `docs/project-knowledge.md`, `docs/architecture.md`, `docs/decision-log.md`, `docs/dec-index.md`, `docs/sprint-history.md`
- Do not modify: Any file under `argus/`, `tests/`, `ui/`, `scripts/`, `config/`

**Config Changes:** No config changes.

**Test Strategy:** No new tests. Verify existing tests still pass.

**Runner Compatibility:**
- Mode: human-in-the-loop (this is a documentation sprint)
- Parallelizable sessions: none
- Estimated token budget: minimal (file copy + targeted edits)

**Dependencies:**
- 17 source files committed to `docs/sprints/sprint-23.1/source/`
- Current docs/decision-log.md with DEC-277 as the last entry

**Escalation Criteria:**
- Any modification to non-documentation files
- DEC entry numbering collision

**Doc Updates Needed:**
- All doc updates ARE the sprint deliverables
- Post-sprint: update Claude.ai project instruction files (manual)
