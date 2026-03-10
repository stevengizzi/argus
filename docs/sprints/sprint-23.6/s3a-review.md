# Tier 2 Review: Sprint 23.6, Session 3a

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session. Do NOT modify any files.
Follow the review skill in .claude/skills/review.md.
Your review report MUST include a structured JSON verdict at the end, fenced with ```json:structured-verdict.

## Review Context
Read `sprint-23.6/review-context.md` for Sprint Spec, Spec by Contradiction, regression checklist, and escalation criteria.

## Tier 1 Close-Out Report
[PASTE THE CLOSE-OUT REPORT HERE AFTER THE IMPLEMENTATION SESSION]

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/intelligence/test_startup.py -x -q`
- Files that should NOT have been modified: anything except `argus/intelligence/startup.py` and test files

## Session-Specific Review Focus
1. Verify factory returns None (not empty components) when disabled
2. Verify each source is only instantiated when its individual `enabled` flag is True
3. Verify classifier handles both ai_client=None and ai_client.enabled=False
4. Verify shutdown helper calls both pipeline.stop() AND storage.close()
5. Verify no import of SystemConfig — factory takes CatalystConfig, not the full system config
6. Verify TYPE_CHECKING guards for ClaudeClient, UsageTracker, EventBus (avoid circular imports)
