# Sprint 23.1: What This Sprint Does NOT Do

## Out of Scope
1. Building `scripts/sprint-runner.py` — deferred to Sprint 23.5
2. Creating `config/runner.yaml` — deferred to Sprint 23.5
3. Modifying any source code under `argus/`, `tests/`, or `ui/`
4. Writing any new tests (documentation-only sprint)
5. Modifying any config files under `config/`
6. Updating Claude.ai project instruction files (done manually by developer
   post-sprint, not by Claude Code)

## Edge Cases to Reject
1. If a DEC number collision is detected: stop and report, do not renumber
2. If an existing file has unexpected format: stop and report, do not reformat

## Scope Boundaries
- Do NOT modify: any file under `argus/`, `tests/`, `ui/`, `scripts/`, `config/`
- Do NOT optimize: any existing code or tests
- Do NOT refactor: any existing documentation structure
- Do NOT add: any Python code, TypeScript code, or test files

## Interaction Boundaries
- This sprint does NOT change the behavior of: any running system, API, or UI
- This sprint does NOT affect: test suite, build process, or deployment

## Deferred to Future Sprints
| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| sprint-runner.py implementation | Sprint 23.5 | N/A |
| runner-config.yaml | Sprint 23.5 | N/A |
| Modified close-out/review skill testing | Sprint 23.5 (first autonomous run) | N/A |
| Claude.ai project file uploads | Manual (post-sprint) | N/A |

---

# Session Breakdown

| Session | Scope | Creates | Modifies | Integrates | Score | Parallelizable |
|---------|-------|---------|----------|------------|-------|----------------|
| S1 | Create all new documentation files from staging | 15 files | None | N/A | ~8 effective* | No |
| S2 | Modify existing repo files + DEC entries | None | 8 files | References S1 files | ~10 effective* | No |

*Score note: Raw scores are inflated because the scoring system is calibrated
for implementation sessions where each file involves design decisions,
integration wiring, and test writing. This sprint involves placing pre-written
content into files and making targeted text additions. Actual cognitive load
per file is ~20% of a typical implementation file.

---

# Sprint-Level Escalation Criteria

Escalate to Tier 3 review if any of the following occur:
1. Any file under `argus/`, `tests/`, `ui/`, `scripts/`, or `config/` is modified
2. DEC numbering collision detected (DEC-278 already exists)
3. Existing skill file structure is altered (not just extended)
4. Any existing test fails after the sprint
5. Files created in wrong directory paths

---

# Sprint-Level Regression Checklist

| Check | How to Verify |
|-------|---------------|
| No source code modified | `git diff --name-only` shows only `docs/` and `.claude/` paths |
| All pytest tests pass | `python -m pytest --tb=short -q` |
| All vitest tests pass | `cd ui && npx vitest run` |
| DEC numbering sequential | Verify DEC-278 through DEC-297 present, no gaps |
| No files outside docs/ and .claude/ changed | `git diff --name-only \| grep -v '^docs/' \| grep -v '^\\.claude/'` returns empty |
| New protocol files exist | 5 specific files verified by name |
| New schema files exist | `ls docs/protocols/schemas/*.md` shows 4 files |
| New template files exist | 4 specific new files verified by name |
| New guide files exist | `ls docs/guides/*.md` shows 2 files |

---

# Doc Update Checklist

All documentation updates ARE the deliverables of this sprint:
- [x] docs/protocols/ — 5 new protocol files (S1)
- [x] docs/protocols/schemas/ — 4 new schema files (S1)
- [x] docs/protocols/templates/ — 4 new template files (S1)
- [x] docs/guides/ — 2 new guide files (S1)
- [x] .claude/skills/close-out.md — structured appendix section (S2)
- [x] .claude/skills/review.md — CONCERNS verdict + structured verdict section (S2)
- [x] .claude/agents/reviewer.md — CONCERNS support (S2)
- [x] docs/project-knowledge.md — runner subsection (S2)
- [x] docs/architecture.md — runner component (S2)
- [x] docs/decision-log.md — DEC-278 through DEC-297 (S2)
- [x] docs/dec-index.md — 20 new entries (S2)
- [x] docs/sprint-history.md — Sprint 23.1 entry (S2)

Post-sprint (manual, not Claude Code):
- [ ] Update Claude.ai project instruction file: sprint-planning.md
- [ ] Update Claude.ai project instruction file: implementation-prompt.md
- [ ] Update Claude.ai project instruction file: review-prompt.md
- [ ] Update Claude.ai project instruction file: in-flight-triage.md
- [ ] Update Claude.ai project instruction file: design-summary.md
