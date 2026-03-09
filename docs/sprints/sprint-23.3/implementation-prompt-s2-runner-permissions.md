# Sprint 23.3, Session 2: Runner Permissions + Timeout Fix

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `.claude/settings.json` (Claude Code project-level settings — check current allowed paths)
   - `scripts/sprint_runner/cli.py` (or whichever module invokes the Claude Code CLI — find the exact invocation command)
   - `scripts/sprint_runner/session.py` (session execution logic)
   - `docs/sprints/sprint-23.5/sprint-23.5-runner-config.yaml` (runner config for Sprint 23.5)
   - `docs/protocols/autonomous-sprint-runner.md` (runner protocol — check what DEC-278+ says about permissions)
   - `CLAUDE.md`
2. Run the runner test suite: `python -m pytest tests/sprint_runner/ -x -q`
   Expected: ~188 tests, all passing
3. Verify you are on the correct branch: `sprint-23.5`

## Objective
Fix the autonomous sprint runner's inability to create new directories by configuring
Claude Code permissions for autonomous execution, and add a session timeout to prevent
indefinite hangs when permission prompts or other interactive prompts block execution.

## Background
The runner invoked Claude Code for Sprint 23.5 Session S1, but Claude Code prompted
for permission to write to `argus/intelligence/__init__.py` (a new directory). In
autonomous mode, nobody is present to approve the prompt, so the session hung
indefinitely. The runner config had `session_timeout_seconds: 0` (no timeout).

## Requirements

### Requirement 1: Configure Claude Code Permissions for Autonomous Execution
Investigate the Claude Code CLI invocation in the runner package and determine the
correct approach:

1. **Check if `--dangerously-skip-permissions` (or equivalent flag) exists** in the
   Claude Code CLI. Search the runner's CLI invocation code and the Claude Code
   documentation (if available in `.claude/`). Sprint 23.2 may have already addressed
   this — check DEC-278 through DEC-297 references in the runner protocol doc.

2. **If a skip-permissions flag exists:** Add it to the runner's CLI invocation
   ONLY when running in autonomous mode. Human-in-the-loop mode should NOT skip
   permissions (the human can approve interactively).

3. **If no such flag exists:** Update `.claude/settings.json` to include the
   `argus/intelligence/` directory (and any other directories Sprint 23.5 creates)
   in the allowed write paths. Also check if there's a wildcard or project-root
   permission that would prevent this class of issue for all future sprints.

4. **Whichever approach is taken:** Document the solution clearly in a code comment
   explaining why the permission handling is configured this way.

### Requirement 2: Set Session Timeout
In the Sprint 23.5 runner config (`docs/sprints/sprint-23.5/sprint-23.5-runner-config.yaml`):

1. Change `session_timeout_seconds` from `0` to `1800` (30 minutes)
2. Verify the runner's session execution code actually enforces this timeout — find
   where the Claude Code subprocess is spawned and confirm there's a timeout mechanism.
   If the timeout is only in config but not enforced in code, that's a code fix too.

### Requirement 3: Verify Runner Can Create New Directories
After applying the permission fix:

1. Do a quick smoke test: verify Claude Code can create a file in
   `argus/intelligence/` without prompting for permission
2. If there are other new directories Sprint 23.5 might create, ensure those are
   also covered

## Constraints
- Do NOT modify: Any files in `argus/` (this session is config/tooling only)
- Do NOT modify: The runner's core logic (session orchestration, triage, etc.)
- Do NOT change: The runner's behavior in human-in-the-loop mode
- The permission fix must be scoped appropriately — don't grant blanket write access
  to the entire filesystem if a more targeted approach works
- This is on the `sprint-23.5` branch, not `main`

## Test Targets
After implementation:
- Existing tests: all runner tests must still pass (`python -m pytest tests/sprint_runner/ -x -q`)
- New tests to write:
  - `test_session_timeout_enforced` — verify timeout config is read and applied to subprocess
  - `test_autonomous_mode_permission_handling` — verify the permission flag/config is applied
    in autonomous mode but not in human-in-the-loop mode (if applicable)
- Minimum new test count: 2
- Test command: `python -m pytest tests/sprint_runner/ -x -q`

## Definition of Done
- [ ] Claude Code can create `argus/intelligence/` directory without interactive prompt
- [ ] Session timeout set to 1800 seconds in Sprint 23.5 runner config
- [ ] Timeout is actually enforced by the runner code (not just config)
- [ ] Permission handling documented in code comments
- [ ] All existing runner tests pass
- [ ] New tests written and passing
- [ ] No modifications to `argus/` application code

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Runner tests pass | `python -m pytest tests/sprint_runner/ -x -q` |
| Human-in-the-loop mode unaffected | Check that permission flag is NOT applied in non-autonomous mode |
| Sprint 23.5 runner config valid | Runner can parse the updated config without errors |
| No application code modified | `git diff argus/` shows no changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
| Check | How to Verify |
|-------|---------------|
| All runner tests pass | `python -m pytest tests/sprint_runner/ -x -q` — 188+ passing |
| Permission handling correct for autonomous mode | Review CLI invocation code |
| Permission handling correct for human-in-the-loop | Verify flag NOT applied |
| Timeout enforced, not just configured | Review subprocess spawning code |
| No application code changes | `git diff argus/` |

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Escalate to Tier 3 if:
1. The permission fix grants blanket write access beyond the project directory
2. Any files in `argus/` were modified
3. The timeout implementation could cause data loss (e.g., killing a session mid-commit)
4. The runner's core orchestration logic was changed
