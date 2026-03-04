# Skill: Documentation Sync

## Trigger
Run this after a sprint completes (all sessions done, Tier 3 review done if needed)
and before starting the next sprint.

## Inputs Required
1. The Doc Update Checklist from the sprint package
2. Access to all project documentation files
3. The close-out reports from all sessions in the sprint
4. The Tier 2 and Tier 3 review reports (if any)

## Procedure

### Step 1: Checklist Execution
For each item on the Doc Update Checklist:
1. Open the specified document
2. Make the specified update
3. Verify the update is accurate and complete
4. Mark the item as done

### Step 2: Decision Log Sync
Scan all close-out reports and review reports for:
- **Judgment calls** that should become DEC entries (any decision that affects future sessions)
- **New risks** identified that should become RSK entries
- **Deferred work** that should become DEF entries

For each new entry, create it in the appropriate log with:
- Next available sequential number (verify no duplicates)
- Full entry including rationale, alternatives (if applicable), cross-references
- Sprint reference (which sprint/session produced this)

### Step 3: Cross-Reference Integrity
Verify:
- [ ] No duplicate DEC/RSK/DEF numbers exist
- [ ] All cross-references between documents point to valid entries
- [ ] Superseded decisions are marked as superseded with pointer to replacement
- [ ] No document references a system state that changed in this sprint without
      reflecting the change
- [ ] Architecture document reflects any structural changes made in this sprint
- [ ] Project status/roadmap reflects sprint completion

### Step 4: Tier A Compression Check
Evaluate the Claude-optimized documents (Tier A — project knowledge, .claude/rules/):
- Are any sections stale (describing superseded state)?
- Has the document grown disproportionately to actual project complexity?
- Are there redundancies that can be compressed?
- Are deprecated or completed items still listed as active?

If yes to any: flag for developer review and suggest specific compressions.
Do NOT compress autonomously — the developer approves Tier A changes.

### Step 5: .claude/rules/ Sync
Check if any new lessons from this sprint should become rules:
- Did the Tier 2 or Tier 3 review flag a pattern that should be prevented?
- Did a diagnostic investigation reveal a class of bug that a rule could prevent?
- Did sprint planning identify a constraint that should persist across sessions?
- Did any "do not modify" constraint prove important enough to be permanent?

For each new rule: create or update the appropriate file in `.claude/rules/`,
following the project's existing rule format.

### Step 6: Produce Sync Report

```
---BEGIN-DOC-SYNC---

**Sprint:** [number]
**Date:** [ISO date]

### Checklist Status
| Item | Status | Notes |
|------|--------|-------|
| [item from checklist] | [DONE/SKIPPED] | [reason if skipped] |

### New Entries Created
- [DEC-NNN: brief description]
- [RSK-NNN: brief description]
- [DEF-NNN: brief description]
(Write "None" if no new entries.)

### Compression Recommendations
[Suggestions for Tier A document compression, or "None needed" if docs are healthy]

### New Rules Added
[List of rules added or updated in .claude/rules/, or "None"]

### Integrity Issues Found
[Any cross-reference problems, numbering gaps, or stale references found and fixed,
or "None — all references intact"]

---END-DOC-SYNC---
```
