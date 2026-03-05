# Skill: Close-Out (Tier 1 Self-Review)

## Trigger
Run this as the FINAL action of every implementation session, after all code changes
are complete and tests pass.

## Pre-Conditions
- All implementation work for this session is complete
- All tests have been run
- All changes have been committed (or are ready to commit)

## Procedure

### Step 1: Generate Close-Out Report
Produce the following report between the markers shown. This exact format is required
for downstream parsing by the Tier 2 review.

**Important:** Render the report inside a fenced code block (triple backticks with `markdown` language hint) so the user can copy/paste it with table formatting preserved.

```
---BEGIN-CLOSE-OUT---

**Session:** [Sprint number] — [Session description]
**Date:** [ISO date]
**Self-Assessment:** [CLEAN | MINOR_DEVIATIONS | FLAGGED]

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| [path] | [added/modified/deleted] | [why] |

### Judgment Calls
Decisions made during implementation that were NOT specified in the prompt:
- [decision]: [rationale]
(Write "None" if all decisions were pre-specified.)

### Scope Verification
Map each spec requirement to the change that implements it:
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| [requirement] | [DONE/PARTIAL/SKIPPED] | [file:function or explanation] |

### Regression Checks
Run each item from the session's regression checklist:
| Check | Result | Notes |
|-------|--------|-------|
| [check description] | [PASS/FAIL] | [details if FAIL] |

### Test Results
- Tests run: [count]
- Tests passed: [count]
- Tests failed: [count]
- New tests added: [count]
- Command used: [exact test command]

### Unfinished Work
Items from the spec that were not completed, and why:
- [item]: [reason]
(Write "None" if all spec items are complete.)

### Notes for Reviewer
Anything the Tier 2 reviewer should pay special attention to:
- [note]
(Write "None" if no special attention needed.)

---END-CLOSE-OUT---
```

### Step 2: Self-Assessment Criteria
Rate your session using these criteria:

- **CLEAN:** All spec requirements met. No judgment calls outside spec. All tests pass.
  All regression checks pass. No unfinished work.
- **MINOR_DEVIATIONS:** All spec requirements met, but minor judgment calls were needed
  (e.g., naming choices, minor implementation details not specified). All tests pass.
- **FLAGGED:** Any of: spec requirement partially met or skipped; test failures;
  regression check failures; significant judgment calls that may affect other sprints;
  scope exceeded; architectural concerns.

### Step 3: Commit
After generating the close-out report:
1. Stage all changes: `git add -A`
2. Commit with message: `[Sprint X.Y] [session scope summary]`
3. Push to remote: `git push`

Do NOT push if self-assessment is FLAGGED — wait for developer review of the close-out.
