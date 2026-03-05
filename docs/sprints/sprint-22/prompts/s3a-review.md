# Tier 2 Review: Sprint 22, Session 3a — Approval Workflow Skeleton

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    docs/sprints/sprint-22/prompts/review-context.md

## Tier 1 Close-Out Report

[PASTE SESSION 3A CLOSE-OUT REPORT HERE]

## Review Scope
- Diff: `git diff HEAD~1 -- argus/ai/actions.py argus/api/routes/ai.py argus/api/ws/ai_chat.py`
- New files: `argus/ai/actions.py`
- Modified: `argus/api/routes/ai.py` (new approve/reject routes), `argus/api/ws/ai_chat.py` (wire ActionManager)
- NOT modified: `argus/core/events.py`, `argus/core/event_bus.py` internals
- Test command: `python -m pytest tests/ai/test_actions.py -x -q`

## Session-Specific Review Focus
1. **CRITICAL:** Verify proposals persisted to DB (not memory-only) per S2 resolution
2. Verify proposal lifecycle: pending → approved/rejected/expired
3. Verify supersession logic: second proposal of same type expires the first
4. Verify TTL enforcement: approve after expiry → 410
5. Verify Event Bus integration: ApprovalRequested/Granted/Denied published (using EXISTING event types, no new ones)
6. Verify expired proposal cleanup on startup
7. Verify periodic expiry cleanup task
8. Verify WS handler now creates proposals for tool_use in TOOLS_REQUIRING_APPROVAL
9. Verify WS handler does NOT create proposals for generate_report
10. Verify approve/reject routes are JWT-protected

## Additional Context
- Implementation prompt for this session: `docs/sprints/sprint-22/prompts/s3a-impl.md`
