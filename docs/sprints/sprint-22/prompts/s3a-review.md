# Tier 2 Review: Sprint 22, Session 3a — Approval Workflow Skeleton

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    docs/sprints/sprint-22/prompts/review-context.md

## Tier 1 Close-Out Report

---BEGIN-CLOSE-OUT---

**Session:** Sprint 22.3a — Approval Workflow Skeleton
**Date:** 2026-03-06
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/ai/actions.py | added | ActionProposal model and ActionManager implementation |
| argus/ai/__init__.py | modified | Export ActionManager, ActionProposal, and exception classes |
| argus/api/routes/ai.py | modified | Added approve/reject/pending endpoints |
| argus/api/dependencies.py | modified | Added action_manager field to AppState |
| argus/api/websocket/ai_chat.py | modified | Wired ActionManager for tool_use proposal creation |
| argus/main.py | modified | Initialize ActionManager on startup, cleanup task lifecycle |
| tests/ai/test_actions.py | added | 19 tests for ActionManager lifecycle |
| tests/api/test_ai_routes.py | modified | 13 new tests for action routes |
| tests/test_main.py | modified | Fixed tests for ActionManager integration |

### Judgment Calls
- Removed FK constraint from ai_action_proposals → ai_conversations: Proposals may be created before conversation is fully persisted; no FK ensures flexibility.
- Fixed `config.ai` → `config.system.ai`: AIConfig is nested under SystemConfig, not directly on ArgusConfig.
- Added `os.environ["ANTHROPIC_API_KEY"] = ""` in test_main.py: Prevents AIConfig auto-enable when real API key is in .env file (via load_dotenv).

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| ai_action_proposals table created on startup | DONE | argus/ai/actions.py:ActionManager._TABLE_SQL |
| ActionManager lifecycle (create/approve/reject/expire) | DONE | argus/ai/actions.py:ActionManager |
| Supersession logic for duplicate action types | DONE | argus/ai/actions.py:create_proposal() |
| Approve/reject REST endpoints (410, 409 errors) | DONE | argus/api/routes/ai.py |
| Event Bus integration | DONE | argus/ai/actions.py publishes events |
| Expired proposals cleaned on startup and periodically | DONE | argus/ai/actions.py:cleanup_expired() and start_cleanup_task() |
| WebSocket creates proposals for tool_use | DONE | argus/api/websocket/ai_chat.py |
| ≥8 new tests | DONE | 32 new tests (19 + 13) |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Existing events unchanged | PASS | events.py not modified |
| Event Bus internals unchanged | PASS | event_bus.py not modified |
| Existing API routes unchanged | PASS | Only added new routes |
| WebSocket still streams correctly | PASS | Existing token streaming preserved |
| All existing tests pass | PASS | 1912 tests passed |

### Test Results
- Tests run: 1912
- Tests passed: 1912
- Tests failed: 0
- New tests added: 32 (19 in test_actions.py, 13 in test_ai_routes.py)
- Command used: `python -m pytest tests/ -x -q`

### Unfinished Work
None

### Notes for Reviewer
- AIConfig has a model_validator that auto-enables AI if ANTHROPIC_API_KEY is set. This caused test failures when the real API key from .env was loaded. Fixed by setting the env var to empty string in test_main.py before any argus.main imports.
- The FK constraint was removed from ai_action_proposals table to avoid constraint failures when proposals are created during streaming before conversation is committed.

---END-CLOSE-OUT---

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
