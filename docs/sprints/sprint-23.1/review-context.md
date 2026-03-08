# Sprint 23.1 Review Context

## Review Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any files.

Follow the review skill in .claude/skills/review.md.

---

## Sprint Spec

### Sprint 23.1: Autonomous Runner Protocol Integration

**Goal:** Integrate all autonomous sprint runner documentation into the ARGUS
repo and update existing files to support dual-mode sprint execution.

**Deliverables:**
1. 15 new documentation files in `docs/protocols/`, `docs/protocols/schemas/`,
   `docs/protocols/templates/`, and `docs/guides/`
2. `.claude/skills/close-out.md` extended with structured JSON appendix section
3. `.claude/skills/review.md` updated: CONCERNS verdict in prose + structured JSON verdict section
4. `.claude/agents/reviewer.md` updated with CONCERNS support
5. `docs/project-knowledge.md` updated with runner subsection
6. `docs/architecture.md` updated with runner component
7. `docs/decision-log.md` updated with DEC-278 through DEC-297 (20 entries)
8. `docs/dec-index.md` updated with 20 new entries
9. `docs/sprint-history.md` updated with Sprint 23.1 entry

---

## Specification by Contradiction

**Out of Scope:**
- Building `scripts/sprint-runner.py` (Sprint 23.5)
- Modifying any source code under `argus/`, `tests/`, or `ui/`
- Writing any new tests
- Modifying any config files under `config/`

**Scope Boundaries:**
- Do NOT modify: any file under `argus/`, `tests/`, `ui/`, `scripts/`, `config/`
- Do NOT add: any Python code, TypeScript code, or test files

---

## Sprint-Level Escalation Criteria

Escalate if:
1. Any file under `argus/`, `tests/`, `ui/`, `scripts/`, or `config/` is modified
2. DEC numbering collision detected
3. Existing skill file structure altered (not just extended)
4. Any existing test fails
5. Files created in wrong paths

---

## Sprint-Level Regression Checklist

| Check | How to Verify |
|-------|---------------|
| No source code modified | `git diff --name-only` shows only `docs/` and `.claude/` paths |
| All pytest pass | `python -m pytest --tb=short -q` |
| All vitest pass | `cd ui && npx vitest run` |
| DEC numbering sequential | Verify DEC-278 through DEC-297 present, no gaps |
| No files outside docs/ and .claude/ | `git diff --name-only \| grep -v '^docs/' \| grep -v '^\\.claude/'` empty |
| New protocol files exist | 5 specific new files verified by name |
| New schema files exist | `ls docs/protocols/schemas/*.md` shows 4 files |
| New template files exist | 4 specific new files verified by name (10 total in templates dir) |
| New guide files exist | `ls docs/guides/*.md` shows 2 files |
