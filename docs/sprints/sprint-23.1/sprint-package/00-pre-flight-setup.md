# Sprint 23.1: Pre-Flight Setup Guide

> Follow these steps before running Session 1.

---

## Step 1: Download Revised Source Files

Download the `source/` directory from the sprint-23.1-revised package. This
contains 17 pre-revised, pre-renumbered documentation files.

## Step 2: Stage Source Files in Repo

```bash
# Create staging directory
mkdir -p docs/sprints/sprint-23.1/source/protocols
mkdir -p docs/sprints/sprint-23.1/source/schemas
mkdir -p docs/sprints/sprint-23.1/source/templates
mkdir -p docs/sprints/sprint-23.1/source/guides
mkdir -p docs/sprints/sprint-23.1/source/modifications
mkdir -p docs/sprints/sprint-23.1/source/decisions

# Place files from the downloaded source/ directory
cp source/protocols/*.md    docs/sprints/sprint-23.1/source/protocols/
cp source/schemas/*.md      docs/sprints/sprint-23.1/source/schemas/
cp source/templates/*.md    docs/sprints/sprint-23.1/source/templates/
cp source/guides/*.md       docs/sprints/sprint-23.1/source/guides/
cp source/modifications/*.md docs/sprints/sprint-23.1/source/modifications/
cp source/decisions/*.md    docs/sprints/sprint-23.1/source/decisions/
```

## Step 3: Stage Review Context File

```bash
cp sprint-package/04-review-context.md docs/sprints/sprint-23.1/review-context.md
```

## Step 4: Verify Staging

```bash
# Verify file counts
echo "Protocols:" && ls docs/sprints/sprint-23.1/source/protocols/*.md | wc -l    # 5
echo "Schemas:" && ls docs/sprints/sprint-23.1/source/schemas/*.md | wc -l        # 4
echo "Templates:" && ls docs/sprints/sprint-23.1/source/templates/*.md | wc -l    # 4
echo "Guides:" && ls docs/sprints/sprint-23.1/source/guides/*.md | wc -l          # 2
echo "Modifications:" && ls docs/sprints/sprint-23.1/source/modifications/*.md | wc -l  # 1
echo "Decisions:" && ls docs/sprints/sprint-23.1/source/decisions/*.md | wc -l    # 1

# Verify DEC renumbering is pre-applied
grep "DEC-278" docs/sprints/sprint-23.1/source/decisions/dec-entries.md  # should match
grep "DEC-277" docs/sprints/sprint-23.1/source/protocols/autonomous-sprint-runner.md  # should NOT match

# Verify review context
ls docs/sprints/sprint-23.1/review-context.md  # should exist
```

## Step 5: Commit Staging

```bash
git add docs/sprints/sprint-23.1/
git commit -m "[Sprint 23.1] Stage source files and review context"
```

## Step 6: Verify Pre-Flight

```bash
# Tests pass
python -m pytest --tb=short -q
cd ui && npx vitest run && cd ..

# Git is clean
git status
```

## Step 7: Execute Sessions

1. Paste `05-implementation-S1.md` into Claude Code → wait for completion
2. Read close-out report → paste into `07-review-prompts.md` (S1 section)
3. Paste S1 review prompt into Claude Code → read verdict
4. If CLEAR: `git add -A && git commit -m "[Sprint 23.1] S1: Create documentation files"`
5. Paste `06-implementation-S2.md` into Claude Code → wait for completion
6. Read close-out report → paste into `07-review-prompts.md` (S2 section)
7. Paste S2 review prompt into Claude Code → read verdict
8. If CLEAR: `git add -A && git commit -m "[Sprint 23.1] S2: Modify existing files + DEC entries"`

## Step 8: Post-Sprint

1. Update Claude.ai project instruction files using `08-updated-project-instructions.md`
2. Update Project Knowledge in this Claude.ai project (Workflow section changes)
3. Sprint complete
