# Sprint 22, Session 2b: Chat API + WebSocket Streaming

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/ai/client.py` (Session 1)
   - `argus/ai/conversations.py` (Session 2a)
   - `argus/ai/usage.py` (Session 2a)
   - `argus/ai/prompts.py` (Session 1)
   - `argus/ai/tools.py` (Session 1)
   - `argus/api/server.py` (startup/lifecycle pattern)
   - `argus/api/dependencies.py` (AppState)
   - `argus/api/ws/` (existing WebSocket handler for pattern reference)
   - `argus/api/routes/` (existing route patterns)
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: ≥1,776 tests (previous + Session 2a), all passing
3. Verify you are on the correct branch: `sprint-22-ai-layer`

## Objective
Create the Chat REST API endpoints, the WebSocket streaming handler for AI chat (with tool_use round-trip support), the usage endpoint, and wire everything into server lifecycle and AppState.

## Requirements

1. In `argus/api/routes/ai.py`, create REST endpoints (all JWT-protected):

   - `POST /api/v1/ai/chat` — Non-streaming chat fallback:
     - Request body: `{conversation_id: str | null, message: str, page: str, page_context: dict}`
     - If `conversation_id` is null, create new conversation (today's date, tag from page mapping)
     - Uses PromptManager to build system prompt + page context + history
     - Calls ClaudeClient.send_message with tools=ARGUS_TOOLS
     - If response contains tool_use blocks: create ActionProposal(s) via ActionManager (Session 3a will implement; for now, store tool_use data in message), provide tool_results, continue conversation
     - Persist user message and assistant response to DB via ConversationManager
     - Record usage via UsageTracker
     - Returns: `{conversation_id, message_id, content: str, tool_use: list | null}`
     - On AI disabled: return 503 with `{error: "AI service not available"}`

   - `GET /api/v1/ai/conversations` — List conversations:
     - Query params: `date_from`, `date_to`, `tag`, `limit` (default 50), `offset` (default 0)
     - Returns: `{conversations: list, total: int}`

   - `GET /api/v1/ai/conversations/{conversation_id}` — Get conversation with messages:
     - Query params: `limit` (default 50), `offset` (default 0)
     - Returns: `{conversation: dict, messages: list}` (messages oldest-first)

   - `GET /api/v1/ai/context/{page}` — Debug: inspect current context payload:
     - Returns the context dict that would be sent for the given page
     - Useful for debugging context injection

   - `GET /api/v1/ai/status` — AI health + cost:
     - Returns: `{enabled: bool, model: str, usage: {today: dict, this_month: dict, per_day_average: float}}`
     - When disabled: `{enabled: false, model: null, usage: null}`

   - `GET /api/v1/ai/usage` — Detailed usage:
     - Query params: `date` (single day) or `year` + `month` (monthly)
     - Returns: `{period: str, input_tokens: int, output_tokens: int, estimated_cost_usd: float, call_count: int, daily_breakdown: list | null}`

2. In `argus/api/ws/ai_chat.py`, create WebSocket chat handler:

   - Endpoint: `WS /ws/v1/ai/chat`
   - Auth: First message must be `{type: "auth", token: "<JWT>"}`. Validate JWT. If invalid, close with 4001 code.
   - Chat message format from client: `{type: "message", conversation_id: str | null, content: str, page: str, page_context: dict}`
   - Response events streamed to client:
     - `{type: "stream_start", conversation_id: str, message_id: str}` — signals start of assistant response
     - `{type: "token", content: str}` — individual token during streaming
     - `{type: "tool_use", tool_name: str, tool_input: dict, proposal_id: str | null}` — action proposal detected (proposal_id populated when ActionManager is wired in Session 3a; for now, null)
     - `{type: "stream_end", full_content: str}` — complete response text
     - `{type: "error", message: str}` — error occurred
   - Streaming flow:
     a. Receive client message
     b. Build system prompt + context via PromptManager
     c. Persist user message to DB (ConversationManager)
     d. Call ClaudeClient.send_message(stream=True, tools=ARGUS_TOOLS)
     e. Stream tokens to client as `{type: "token"}` events
     f. If tool_use block detected in stream:
        - Send `{type: "tool_use"}` event to client
        - Create tool_result: `{type: "tool_result", tool_use_id: <id>, content: "Proposal created. Awaiting operator approval."}`
        - For `generate_report`: result is `"Report generation queued."`
        - Call ClaudeClient.send_with_tool_results to continue the conversation
        - Continue streaming the continuation
     g. On stream complete: persist full assistant message, record usage, send `{type: "stream_end"}`
   - Cancellation: if client closes connection or sends `{type: "cancel"}`, abort the Claude API call
   - Timeout: 60-second timeout on Claude API response
   - One active stream per connection. If client sends new message while streaming, cancel current stream.
   - Connection management: track active connections, clean up on disconnect

3. In `argus/api/dependencies.py`, add AI services to AppState:
   - Add `ai_client: ClaudeClient | None`
   - Add `conversation_manager: ConversationManager | None`
   - Add `usage_tracker: UsageTracker | None`
   - Add `prompt_manager: PromptManager | None`
   - Add `context_builder: SystemContextBuilder | None`
   - All None when AI disabled

4. In `argus/api/server.py`, add AI lifecycle:
   - On startup: if AIConfig.enabled, initialize ClaudeClient, ConversationManager (+ DB tables), UsageTracker (+ DB table), PromptManager, SystemContextBuilder. Store in AppState.
   - On shutdown: clean up (close any active WS connections, etc.)
   - If ANTHROPIC_API_KEY not set: log "AI services disabled — no API key" and continue startup normally

5. Register the WebSocket endpoint alongside the existing `/ws/v1/live` endpoint. The new endpoint is `/ws/v1/ai/chat`. Ensure the existing WS handler is completely untouched.

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/execution/`, `argus/data/`, `argus/backtest/`, `argus/core/event_bus.py`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`
- Do NOT modify: existing API routes or their signatures. Only ADD new routes in `ai.py`.
- Do NOT modify: existing WebSocket handler (`/ws/v1/live`). The new WS is completely separate.
- Do NOT change: existing AppState fields or their behavior.
- tool_use → ActionProposal wiring is a STUB in this session. Session 3a will implement ActionManager. For now, tool_use events are passed through to the client but proposals are not yet created/persisted. Mark stubs with `# TODO(Session 3a): Wire ActionManager here`.

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `tests/api/test_ai_routes.py`: POST /chat (happy path with mock, error when disabled, auth required), GET /conversations (list, filter by date/tag), GET /conversations/{id} (with messages), GET /context/{page}, GET /status (enabled + disabled), GET /usage
  - `tests/api/test_ai_ws.py`: WS auth flow (valid token, invalid token → 4001), message → streaming response, cancel mid-stream, tool_use event propagation, timeout handling
- Minimum new test count: 10
- Test command: `python -m pytest tests/api/test_ai_routes.py tests/api/test_ai_ws.py -x -q`

## Definition of Done
- [ ] All REST endpoints created and JWT-protected
- [ ] WebSocket handler streams tokens from Claude API
- [ ] tool_use blocks detected and forwarded to client (stub — no ActionManager yet)
- [ ] Usage tracked for all API calls
- [ ] AI services wired into AppState and server lifecycle
- [ ] System starts normally with AI disabled (no key)
- [ ] Existing WebSocket `/ws/v1/live` completely unaffected
- [ ] All existing tests pass
- [ ] ≥10 new tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing WS unaffected | Connect to `/ws/v1/live` — works as before |
| Existing API routes unchanged | Run existing API tests — all pass |
| Auth on all new endpoints | Hit each new endpoint without token → 401 |
| AI-disabled startup clean | Unset key, start, verify no errors in logs |
| All existing tests pass | `python -m pytest tests/ -x -q` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
[See 06-regression-checklist.md]

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
[See 05-escalation-criteria.md]
