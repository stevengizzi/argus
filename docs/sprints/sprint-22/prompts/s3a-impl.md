# Sprint 22, Session 3a: Approval Workflow Skeleton

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/ai/tools.py` (Session 1 — tool definitions, TOOLS_REQUIRING_APPROVAL)
   - `argus/ai/conversations.py` (Session 2a)
   - `argus/api/routes/ai.py` (Session 2b — existing routes)
   - `argus/api/ws/ai_chat.py` (Session 2b — tool_use stubs to wire)
   - `argus/core/events.py` (existing ApprovalRequested/Granted/Denied events)
   - `argus/core/event_bus.py` (publish/subscribe pattern)
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: ≥1,786 tests (previous + Session 2b), all passing
3. Verify you are on the correct branch: `sprint-22-ai-layer`

## Objective
Create the ActionProposal model with DB persistence, ActionManager lifecycle (create, approve, reject, expire), approve/reject API routes, Event Bus integration, and startup cleanup for expired proposals. Wire into the Session 2b WebSocket handler's tool_use stubs.

## Requirements

1. In `argus/ai/actions.py`, create `ActionProposal` model and `ActionManager`:

   - DB table `ai_action_proposals`:
     ```sql
     CREATE TABLE IF NOT EXISTS ai_action_proposals (
         id TEXT PRIMARY KEY,           -- ULID
         conversation_id TEXT NOT NULL,
         message_id TEXT,               -- The assistant message that contained the tool_use
         tool_name TEXT NOT NULL,       -- e.g., 'propose_allocation_change'
         tool_use_id TEXT NOT NULL,     -- Claude's tool_use_id for correlation
         tool_input TEXT NOT NULL,      -- JSON: the tool input parameters
         status TEXT NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, expired, executed, failed
         result TEXT,                   -- JSON: execution result (after approve+execute)
         failure_reason TEXT,           -- If status is 'failed'
         created_at TEXT NOT NULL,
         expires_at TEXT NOT NULL,      -- created_at + TTL
         resolved_at TEXT,             -- When approved/rejected/expired
         FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id)
     );
     CREATE INDEX IF NOT EXISTS idx_proposals_status ON ai_action_proposals(status);
     CREATE INDEX IF NOT EXISTS idx_proposals_conversation ON ai_action_proposals(conversation_id);
     ```

   - `ActionProposal` dataclass/Pydantic model:
     ```python
     class ActionProposal:
         id: str
         conversation_id: str
         message_id: str | None
         tool_name: str
         tool_use_id: str
         tool_input: dict
         status: str  # pending, approved, rejected, expired, executed, failed
         result: dict | None
         failure_reason: str | None
         created_at: datetime
         expires_at: datetime
         resolved_at: datetime | None
     ```

   - `ActionManager`:
     - Constructor takes `db_path`, `event_bus`, `config: AIConfig`
     - `async def initialize()` — create table, clean up expired proposals from previous runs
     - `async def create_proposal(conversation_id: str, message_id: str | None, tool_name: str, tool_use_id: str, tool_input: dict) -> ActionProposal`:
       - Validate tool_name is in TOOLS_REQUIRING_APPROVAL (if not, raise error)
       - Check for existing pending proposal of same tool_name — if found, supersede it (mark 'expired' with note "Superseded by new proposal")
       - Create proposal with expires_at = now + TTL
       - Persist to DB
       - Publish ApprovalRequested event on Event Bus
       - Return proposal
     - `async def approve_proposal(proposal_id: str) -> ActionProposal`:
       - Load from DB
       - If status != 'pending': raise error with current status
       - If expired (now > expires_at): mark as 'expired', raise error "Proposal expired"
       - Mark as 'approved', set resolved_at
       - Publish ApprovalGranted event
       - Return updated proposal (execution happens in Session 3b executors)
     - `async def reject_proposal(proposal_id: str, reason: str = "") -> ActionProposal`:
       - Load, validate pending, mark 'rejected', set resolved_at
       - Publish ApprovalDenied event
       - Return
     - `async def execute_proposal(proposal_id: str, result: dict) -> ActionProposal`:
       - Load, validate status is 'approved'
       - Mark 'executed', store result
       - Persist, return
     - `async def fail_proposal(proposal_id: str, reason: str) -> ActionProposal`:
       - Load, mark 'failed', store failure_reason
       - Persist, return
     - `async def get_proposal(proposal_id: str) -> ActionProposal | None`
     - `async def get_pending_proposals(conversation_id: str | None = None) -> list[ActionProposal]`
     - `async def cleanup_expired()` — find all pending proposals past expires_at, mark as 'expired'
     - Run cleanup on initialize() and periodically (every 30s via asyncio task)

2. Add approve/reject routes to `argus/api/routes/ai.py`:
   - `POST /api/v1/ai/actions/{proposal_id}/approve`:
     - JWT required
     - Calls ActionManager.approve_proposal
     - Returns: `{proposal: dict, status: "approved"}`
     - If expired: 410 Gone with `{error: "Proposal expired"}`
     - If not pending: 409 Conflict with `{error: "Proposal is {status}"}`
   - `POST /api/v1/ai/actions/{proposal_id}/reject`:
     - JWT required
     - Request body: `{reason: str}` (optional)
     - Calls ActionManager.reject_proposal
     - Returns: `{proposal: dict, status: "rejected"}`
   - `GET /api/v1/ai/actions/pending`:
     - JWT required
     - Returns all pending proposals: `{proposals: list}`

3. Wire ActionManager into AppState and server lifecycle:
   - Add `action_manager: ActionManager | None` to AppState
   - Initialize on startup if AI enabled
   - Start periodic expiry cleanup task on startup, cancel on shutdown

4. Wire into Session 2b WebSocket stubs:
   - In `argus/api/ws/ai_chat.py`, replace `# TODO(Session 3a): Wire ActionManager here` stubs:
   - When a tool_use block is detected during streaming:
     a. If tool_name is in TOOLS_REQUIRING_APPROVAL: call `action_manager.create_proposal()`
     b. Send `{type: "tool_use", tool_name, tool_input, proposal_id: proposal.id}` to client
     c. Return tool_result to Claude: `"Proposal #{proposal.id} created. Awaiting operator approval."`
     d. If tool_name is NOT in TOOLS_REQUIRING_APPROVAL (e.g., generate_report): send tool_use event with `proposal_id: null`, return tool_result `"Report generation queued."` (execution in Session 3b)

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/execution/`, `argus/data/`, `argus/backtest/`, `argus/core/event_bus.py` internals, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`
- Do NOT modify: existing Event types (ApprovalRequested/Granted/Denied already exist in events.py — use them as-is)
- Do NOT implement actual action execution in this session. ActionManager.approve_proposal marks 'approved' but does NOT execute. Execution is Session 3b.

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `tests/ai/test_actions.py`:
    - Create proposal (happy path)
    - Create proposal supersedes existing pending of same type
    - Approve proposal (happy path, publishes event)
    - Approve expired proposal → error
    - Approve already-approved → error
    - Reject proposal (happy path)
    - Expire cleanup finds and marks stale proposals
    - DB persistence survives "restart" (close and reopen manager)
    - Proposal TTL respects config
  - `tests/api/test_ai_routes.py` (extend): approve endpoint, reject endpoint, pending list, auth required, error cases
- Minimum new test count: 8
- Test command: `python -m pytest tests/ai/test_actions.py tests/api/test_ai_routes.py -x -q`

## Definition of Done
- [ ] ai_action_proposals table created on startup
- [ ] ActionManager lifecycle: create → approve/reject/expire
- [ ] Supersession logic for duplicate action types
- [ ] Approve/reject REST endpoints with proper error handling (410, 409)
- [ ] Event Bus integration (ApprovalRequested/Granted/Denied published)
- [ ] Expired proposals cleaned on startup and periodically
- [ ] WebSocket handler creates proposals for tool_use requiring approval
- [ ] All existing tests pass
- [ ] ≥8 new tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing events unchanged | Check events.py — no modifications |
| Event Bus internals unchanged | Check event_bus.py — no modifications |
| Existing API routes unchanged | Run existing route tests |
| WebSocket still streams correctly | Connect, send message, verify token streaming works |
| All existing tests pass | `python -m pytest tests/ -x -q` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
[See 06-regression-checklist.md]

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
[See 05-escalation-criteria.md]
