# Tier 2 Review: Sprint 23.3, Session 2 — Runner Permissions + Timeout Fix

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

## Review Context

**Sprint Goal:** Fix the autonomous sprint runner's inability to create new
directories and add session timeout to prevent indefinite hangs.

**What This Sprint Does NOT Do:**
- Does NOT modify any files in `argus/` (application code)
- Does NOT change the runner's core orchestration logic
- Does NOT change human-in-the-loop mode behavior

**Regression Checklist:**
| Check | How to Verify |
|-------|---------------|
| All runner tests pass | `python -m pytest tests/sprint_runner/ -x -q` — 188+ passing |
| Permission handling correct for autonomous mode | Review CLI invocation code |
| Permission handling correct for human-in-the-loop | Verify flag NOT applied |
| Timeout enforced, not just configured | Review subprocess spawning code |
| No application code changes | `git diff argus/` |

**Escalation Criteria:**
Escalate to Tier 3 if:
1. The permission fix grants blanket write access beyond the project directory
2. Any files in `argus/` were modified
3. The timeout implementation could cause data loss (e.g., killing a session mid-commit)
4. The runner's core orchestration logic was changed

## Tier 1 Close-Out Report
---BEGIN-CLOSE-OUT---

**Session:** Sprint 23.3 — S2 Runner Permissions + Timeout Fix
**Date:** 2026-03-09
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| scripts/sprint_runner/executor.py | modified | Add `--dangerously-skip-permissions` flag for autonomous mode |
| docs/sprints/sprint-23.5/sprint-23.5-runner-config.yaml | modified | Set session_timeout_seconds to 1800 (30 min) |
| tests/sprint_runner/test_executor.py | modified | Add 2 new tests for timeout + permission handling |

### Judgment Calls
None — all decisions were pre-specified in the implementation prompt. The prompt specified using `--dangerously-skip-permissions` if such a flag exists, which it does.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Configure Claude Code permissions for autonomous execution | DONE | executor.py:279-280 — adds `--dangerously-skip-permissions` when mode is autonomous |
| Permission flag NOT applied in human-in-the-loop mode | DONE | executor.py:279 — condition checks `mode == "autonomous"` only |
| Document permission handling in code comments | DONE | executor.py:275-277 — inline comment explaining the rationale |
| Set session timeout to 1800 in Sprint 23.5 config | DONE | sprint-23.5-runner-config.yaml:26 |
| Verify timeout is enforced in code | DONE | Code review confirmed asyncio.wait_for() with timeout; test added |
| Write test_session_timeout_enforced | DONE | test_executor.py:test_session_timeout_enforced |
| Write test_autonomous_mode_permission_handling | DONE | test_executor.py:test_autonomous_mode_permission_handling |
| No modifications to argus/ | DONE | `git diff argus/` shows no changes |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Runner tests pass | PASS | 190 passed (188 + 2 new) |
| Human-in-the-loop mode unaffected | PASS | Flag NOT added when mode != "autonomous" |
| Sprint 23.5 runner config valid | PASS | Config parses successfully |
| No application code modified | PASS | `git diff argus/` is empty |

### Test Results
- Tests run: 2302
- Tests passed: 2302
- Tests failed: 0
- New tests added: 2
- Command used: `python -m pytest tests/sprint_runner/ -x -q`

### Unfinished Work
None — all spec items are complete.

### Notes for Reviewer
None — straightforward implementation of documented CLI flag usage.

---END-CLOSE-OUT---

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/sprint_runner/ -x -q`
- Files that should NOT have been modified:
  - Any file in `argus/`
  - `scripts/sprint-runner.py` (entry point — should not need changes)
  - Core runner modules other than CLI invocation and session execution

## Session-Specific Review Focus
1. **Verify permission scope is appropriate:** If using `--dangerously-skip-permissions`
   or equivalent, verify it's ONLY applied in autonomous mode. If using settings.json,
   verify the allowed paths are scoped to the project directory, not broader.
2. **Verify timeout is enforced in code:** The runner config having `session_timeout_seconds: 1800`
   is necessary but not sufficient. The subprocess spawning code must actually use this
   value. Check that it's not just stored and ignored.
3. **Verify timeout behavior is safe:** When a session times out, what happens? Check
   that the runner doesn't leave partial state (uncommitted changes, dangling processes).
4. **Verify human-in-the-loop mode is unaffected:** The permission flag should not be
   applied when the runner is in HITL mode.
5. **Check no application code was touched:** `git diff argus/` must be empty.

## Additional Context
This issue was discovered when the Sprint 23.5 autonomous run hung at 8:46 PM waiting
for a permission approval that nobody was present to grant. The session had
`session_timeout_seconds: 0` (infinite), so it would have waited forever. This is a
config/tooling fix on the `sprint-23.5` branch, separate from the Session 1 code
changes on `main`.
