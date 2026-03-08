# Sprint 23.1, Session 1: Create New Documentation Files

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/project-knowledge.md` (verify Sprint 23/23.05 complete)
   - `docs/decision-log.md` (verify DEC-277 is the last entry)
2. Run the test suite: `python -m pytest --tb=short -q && cd ui && npx vitest run && cd ..`
   Expected: 2101 pytest + 392 vitest (approximately), all passing
3. Verify you are on the correct branch: `main`
4. Verify staging source files exist:
   `ls docs/sprints/sprint-23.1/source/`
   Expected: `protocols/`, `schemas/`, `templates/`, `guides/`, `modifications/`, `decisions/`
5. Verify source files are pre-renumbered (DEC-278+, not DEC-277):
   `grep "DEC-278" docs/sprints/sprint-23.1/source/decisions/dec-entries.md`
   Expected: matches found

## Objective
Create 15 new documentation files by reading pre-written content from the
staging directory and placing them in their final repo locations. The source
files are already pre-renumbered with correct DEC references — this session
is a pure file-copy operation.

## Requirements

### 1. Create destination directories
```bash
mkdir -p docs/protocols/schemas
mkdir -p docs/protocols/templates
mkdir -p docs/guides
```

(Note: `docs/protocols/` and `docs/protocols/templates/` already exist with
existing files. Only `docs/protocols/schemas/` and `docs/guides/` are new.)

### 2. Place protocol files (5 files)
For each file, read from staging and write to final location:

| Source | Destination |
|--------|------------|
| `docs/sprints/sprint-23.1/source/protocols/autonomous-sprint-runner.md` | `docs/protocols/autonomous-sprint-runner.md` |
| `docs/sprints/sprint-23.1/source/protocols/notification-protocol.md` | `docs/protocols/notification-protocol.md` |
| `docs/sprints/sprint-23.1/source/protocols/tier-2.5-triage.md` | `docs/protocols/tier-2.5-triage.md` |
| `docs/sprints/sprint-23.1/source/protocols/spec-conformance-check.md` | `docs/protocols/spec-conformance-check.md` |
| `docs/sprints/sprint-23.1/source/protocols/run-log-specification.md` | `docs/protocols/run-log-specification.md` |

### 3. Place schema files (4 files)

| Source | Destination |
|--------|------------|
| `docs/sprints/sprint-23.1/source/schemas/structured-closeout-schema.md` | `docs/protocols/schemas/structured-closeout-schema.md` |
| `docs/sprints/sprint-23.1/source/schemas/structured-review-verdict-schema.md` | `docs/protocols/schemas/structured-review-verdict-schema.md` |
| `docs/sprints/sprint-23.1/source/schemas/run-state-schema.md` | `docs/protocols/schemas/run-state-schema.md` |
| `docs/sprints/sprint-23.1/source/schemas/runner-config-schema.md` | `docs/protocols/schemas/runner-config-schema.md` |

### 4. Place template files (4 files)

| Source | Destination |
|--------|------------|
| `docs/sprints/sprint-23.1/source/templates/tier-2.5-triage-prompt.md` | `docs/protocols/templates/tier-2.5-triage-prompt.md` |
| `docs/sprints/sprint-23.1/source/templates/spec-conformance-prompt.md` | `docs/protocols/templates/spec-conformance-prompt.md` |
| `docs/sprints/sprint-23.1/source/templates/doc-sync-automation-prompt.md` | `docs/protocols/templates/doc-sync-automation-prompt.md` |
| `docs/sprints/sprint-23.1/source/templates/fix-prompt.md` | `docs/protocols/templates/fix-prompt.md` |

### 5. Place guide files (2 files)

| Source | Destination |
|--------|------------|
| `docs/sprints/sprint-23.1/source/guides/autonomous-process-guide.md` | `docs/guides/autonomous-process-guide.md` |
| `docs/sprints/sprint-23.1/source/guides/human-in-the-loop-process-guide.md` | `docs/guides/human-in-the-loop-process-guide.md` |

### 6. Verify

After all 15 files are placed:
1. Verify new protocol files: `ls docs/protocols/autonomous-sprint-runner.md docs/protocols/notification-protocol.md docs/protocols/tier-2.5-triage.md docs/protocols/spec-conformance-check.md docs/protocols/run-log-specification.md` — all 5 should exist
2. Verify new schema files: `ls docs/protocols/schemas/*.md` — 4 files
3. Verify new template files: `ls docs/protocols/templates/fix-prompt.md docs/protocols/templates/tier-2.5-triage-prompt.md docs/protocols/templates/spec-conformance-prompt.md docs/protocols/templates/doc-sync-automation-prompt.md` — all 4 should exist
4. Verify new guide files: `ls docs/guides/*.md` — 2 files
5. Verify DEC references are correct: `grep -r "DEC-278" docs/protocols/autonomous-sprint-runner.md` — should return results (confirming runner architecture is DEC-278)
6. Verify NO DEC-277 in new files: `grep -r "DEC-277" docs/protocols/ docs/protocols/schemas/ docs/guides/` — should return NO results (DEC-277 only exists in existing files and refers to a different decision)

## Constraints
- Do NOT modify: any file under `argus/`, `tests/`, `ui/`, `scripts/`, `config/`
- Do NOT modify: any existing file under `docs/` or `.claude/` (only create new files)
- Do NOT create: any Python, TypeScript, or test files
- Do NOT apply any DEC renumbering (source files are pre-renumbered)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests: none (documentation-only session)
- Test command: `python -m pytest --tb=short -q && cd ui && npx vitest run`

## Definition of Done
- [ ] All 15 files created at correct paths
- [ ] No DEC-277 references in new files
- [ ] Directory structure verified (schemas/, guides/ directories exist)
- [ ] All existing tests pass
- [ ] No existing files modified

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No source code modified | `git diff --name-only` shows only new `docs/` paths |
| 5 new protocol files | Verify each exists by name |
| 4 new schema files | `ls docs/protocols/schemas/*.md \| wc -l` = 4 |
| 4 new template files | Verify each exists by name (6 existed before + 4 new = 10 total) |
| 2 new guide files | `ls docs/guides/*.md \| wc -l` = 2 |
| DEC refs correct | `grep -r "DEC-277" docs/protocols/ docs/protocols/schemas/ docs/guides/` returns nothing |
| All tests pass | pytest + vitest both pass |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
| Check | How to Verify |
|-------|---------------|
| No source code modified | `git diff --name-only` shows only `docs/` and `.claude/` paths |
| All pytest pass | `python -m pytest --tb=short -q` |
| All vitest pass | `cd ui && npx vitest run` |
| DEC numbering sequential | Verify DEC-278 through DEC-297 present in final sprint, no gaps |
| No files outside docs/ and .claude/ | `git diff --name-only \| grep -v '^docs/' \| grep -v '^\\.claude/'` empty |
| New protocol files exist | Verify 5 specific new files by name |
| New schema files exist | `ls docs/protocols/schemas/*.md` shows 4 files |
| New template files exist | Verify 4 specific new template files by name |
| New guide files exist | `ls docs/guides/*.md` shows 2 files |

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Escalate if:
1. Any file under `argus/`, `tests/`, `ui/`, `scripts/`, or `config/` is modified
2. DEC numbering collision detected (DEC-278 already exists in repo)
3. Existing skill or protocol file structure is altered (not just new files added)
4. Any existing test fails after the sprint
5. Files created in wrong directory paths
