# Tier 2 Review: Sprint 23.8, Session 2

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-23.8-review-context.md`

## Tier 1 Close-Out Report
[PASTE THE CLOSE-OUT REPORT HERE AFTER THE IMPLEMENTATION SESSION]

## Review Scope
- Diff to review: `git diff HEAD~1` (or the appropriate range for Session 2 commits)
- Test command: `python -m pytest tests/intelligence/ -x -q -k "classifier"`
- Files that should NOT have been modified: `argus/ai/usage.py`, `argus/ai/claude_client.py`, `startup.py`, `server.py`, `storage.py`, source files, `core/`, `strategies/`, `execution/`, `ui/`

## Session-Specific Review Focus
1. Verify cost ceiling check happens BEFORE each Claude API call, not after — checking after would allow overspend
2. Verify the cost comparison uses `>=` (not `>`) against `daily_cost_ceiling_usd` — at-ceiling should trigger fallback
3. Verify that when the ceiling is reached mid-batch, remaining items are classified via rule-based fallback — NOT dropped, NOT skipped, NOT left unclassified
4. Verify `record_usage()` is called with the correct parameters matching the UsageTracker interface — check `argus/ai/usage.py` for the method signature
5. Verify ALL `usage_tracker` access is guarded with `if self._usage_tracker is not None` — search for every `usage_tracker` reference in the diff
6. Verify that `usage_tracker=None` does NOT produce any log warnings — this is a normal operating mode (AI disabled), not an error condition
7. Verify the cycle cost log includes both the dollar amount and the Claude vs fallback item counts
8. Verify no modifications were made to the UsageTracker interface (`argus/ai/usage.py`) — this is an escalation trigger if it was changed
9. Verify the rule-based fallback classifier still functions independently (existing tests should cover this)

## Additional Context
During the March 12 QA session, 336 items were classified via Claude API with zero cost tracking. The daily cost ceiling ($5/day, DEC-303) was specified in the sprint 23.5 design but was never wired into the classification path. This session completes that wiring.

The UsageTracker was built in Sprint 22 for the AI Copilot layer. It records per-call costs to `argus.db`. The classifier needs to use the same tracker — if the interface doesn't support what's needed (e.g., it only tracks chat-style usage, not classification calls), that's an escalation trigger per the sprint spec.
