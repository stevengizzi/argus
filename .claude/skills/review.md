# Skill: Review (Tier 2 Diff-Based Review)

## Trigger
Run this in a FRESH session (or as a subagent) after an implementation session completes.
This session is READ-ONLY. Do not modify any code.

## Inputs Required
Before starting, you need:
1. The Sprint Spec for the session being reviewed
2. The Tier 1 Close-Out Report (between ---BEGIN-CLOSE-OUT--- and ---END-CLOSE-OUT--- markers)
3. The Sprint-Level Regression Checklist
4. The Sprint-Level Escalation Criteria

## Procedure

### Step 1: Gather Context
1. Read the sprint spec
2. Read the close-out report
3. Run `git diff HEAD~1` (or the appropriate range) to see all changes
4. Run the full test suite
5. Read the sprint-level regression checklist

### Step 2: Evaluate
For each of the following, assess PASS or FAIL:

**Scope Compliance**
- Do the changes match the spec requirements? (Check against close-out Scope Verification)
- Were any files modified that are outside the spec's scope?
- Were any "do not modify" constraints violated?

**Close-Out Accuracy**
- Does the change manifest match the actual diff?
- Are all judgment calls documented?
- Is the self-assessment rating justified?

**Test Health**
- Do all tests pass when you run them now?
- Is test count consistent with the close-out report?
- Are new tests meaningful (not trivial or tautological)?

**Regression Checklist**
- Run every item on the sprint-level regression checklist
- Flag any failures

**Architectural Compliance**
- Do changes respect the project's architectural constraints?
- Are interfaces, naming conventions, and patterns consistent with the codebase?
- Is new technical debt introduced? If so, is it tracked?

**Escalation Criteria Check**
- Evaluate every item on the sprint-level escalation criteria list
- If ANY escalation criterion is met, the verdict MUST be ESCALATE

**Verdict Determination**
Based on all assessments above, determine the verdict:
- **CLEAR:** All categories PASS. No findings with severity HIGH or CRITICAL.
- **CONCERNS:** All critical functions work, but one or more MEDIUM-severity
  findings exist (correctness concerns, test coverage gaps, error handling
  issues that don't rise to spec violation or escalation).
- **ESCALATE:** ANY CRITICAL finding, ANY escalation criterion triggered,
  regression checklist failure, or "do not modify" constraint violation.

### Step 3: Produce Review Report
Produce the following report between the markers shown. This exact format is required
for downstream parsing.

**Important:** Render the report inside a fenced code block (triple backticks with `markdown` 
language hint) so the user can copy/paste it with table formatting preserved.

```
---BEGIN-REVIEW---

**Reviewing:** [Sprint X.Y] — [session description]
**Reviewer:** Tier 2 Automated Review
**Date:** [ISO date]
**Verdict:** [CLEAR | CONCERNS | ESCALATE]

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | [PASS/FAIL] | [notes] |
| Close-Out Accuracy | [PASS/FAIL] | [notes] |
| Test Health | [PASS/FAIL] | [notes] |
| Regression Checklist | [PASS/FAIL] | [notes] |
| Architectural Compliance | [PASS/FAIL] | [notes] |
| Escalation Criteria | [NONE_TRIGGERED / TRIGGERED: list] | [notes] |

### Findings
[Detailed findings, organized by severity. Include specific file paths and line
references where relevant.]

### Recommendation
[If CLEAR: "Proceed to next session."
 If CONCERNS: description of medium-severity concerns and recommended actions.
 If ESCALATE: specific description of what needs Tier 3 review and why.]

---END-REVIEW---
```

### Step 4: Do Not Modify Code
This is a review session. If you find issues, document them in the review report.
Do NOT fix them. Fixes happen in the next planned session or an impromptu session,
with their own close-out and review cycle.

## Structured Review Verdict

After producing the human-readable review report above, append a machine-
parseable JSON block. This block is used by the autonomous runner for automated
decision-making.

Fence the block with:

    ```json:structured-verdict
    {
      "schema_version": "1.0",
      "sprint": "[sprint number]",
      "session": "[session ID]",
      "verdict": "CLEAR | CONCERNS | ESCALATE",
      "findings": [
        {
          "description": "...",
          "severity": "INFO | LOW | MEDIUM | HIGH | CRITICAL",
          "category": "SPEC_VIOLATION | SCOPE_BOUNDARY_VIOLATION | REGRESSION | TEST_COVERAGE_GAP | ERROR_HANDLING | PERFORMANCE | NAMING_CONVENTION | ARCHITECTURE | SECURITY | OTHER",
          "file": "path (optional)",
          "recommendation": "..."
        }
      ],
      "spec_conformance": {
        "status": "CONFORMANT | MINOR_DEVIATION | MAJOR_DEVIATION",
        "notes": "...",
        "spec_by_contradiction_violations": []
      },
      "files_reviewed": ["path1", "path2"],
      "files_not_modified_check": {
        "passed": true | false,
        "violations": []
      },
      "tests_verified": {
        "all_pass": true | false,
        "count": [N],
        "new_tests_adequate": true | false,
        "test_quality_notes": "..."
      },
      "regression_checklist": {
        "all_passed": true | false,
        "results": [
          {"check": "...", "passed": true | false, "notes": "..."}
        ]
      },
      "escalation_triggers": [],
      "recommended_actions": []
    }
    ```

Rules for the structured verdict:
- Always produce it, even in human-in-the-loop mode
- The verdict must match the overall assessment in the human-readable report
- CLEAR: no findings with severity HIGH or CRITICAL
- CONCERNS: one or more MEDIUM findings, no CRITICAL
- ESCALATE: any CRITICAL finding, or specific escalation criteria met
- files_not_modified_check.passed must be false if any protected file was changed
- regression_checklist must reflect actual test execution, not assumptions
