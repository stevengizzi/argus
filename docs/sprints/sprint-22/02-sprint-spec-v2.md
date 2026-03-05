# Sprint 22: AI Layer MVP + Copilot Activation

## Goal
Activate the AI Layer — connect the Copilot shell (built Sprint 21d) to Claude API with streaming responses via WebSocket, persistent conversation history, page-aware context injection across all 7 Command Center pages, and a full approval workflow for AI-proposed actions using Claude's native tool_use API. Add AI-generated daily summaries to the Debrief and an AI insight card to the Dashboard. Track all API costs from day one. This is the sprint that makes ARGUS intelligent.

## Scope

### Deliverables

1. **Claude API integration module** (`argus/ai/`) — ClaudeClient wrapper with tool_use support, PromptManager with template-based prompt construction including defined system prompt template (ARGUS description, operator context, strategy summaries, behavioral guardrails), SystemContextBuilder for injecting live system state with per-section token budgets (system ≤1,500 tokens, page context ≤2,000 tokens, history ≤8,000 tokens, response ≤4,096 tokens), ResponseCache with TTL-based expiry, AIConfig Pydantic model with all configuration including token budgets and cost estimation rates.

2. **Tool definitions module** (`argus/ai/tools.py`) — Claude tool_use function definitions for the 5 allowed action types: `propose_allocation_change` (strategy_allocation_override), `propose_risk_param_change` (risk_param_update), `propose_strategy_suspend` (strategy_suspend), `propose_strategy_resume` (strategy_resume), `generate_report` (report generation). Each tool has a JSON schema with input validation. System prompt instructs Claude to only use these tools when proposing executable actions.

3. **Persistent chat infrastructure** — `ai_conversations`, `ai_messages`, and `ai_usage` aiosqlite tables. ConversationManager service (CRUD + pagination). Conversations keyed by calendar date with optional tag field ("pre-market", "session", "research", "debrief", "general"). UsageTracker recording input_tokens, output_tokens, model, estimated_cost_usd per API call. Full history queryable.

4. **WebSocket streaming endpoint** — `WS /ws/v1/ai/chat` with JWT auth (token in initial message, matching existing WS auth pattern). Proxies Claude API streaming response token-by-token. Handles tool_use round-trips transparently: when Claude emits a tool_use block, backend creates an ActionProposal, returns a tool_result to Claude, and continues streaming. Handles cancellation (client close frame), timeouts, and partial responses.

5. **Chat REST API** — `POST /api/v1/ai/chat` (non-streaming fallback), `GET /api/v1/ai/conversations` (list with date/tag filtering), `GET /api/v1/ai/conversations/{id}` (with messages + pagination), `GET /api/v1/ai/context/{page}` (debug/inspect current context payload), `GET /api/v1/ai/status` (health + current-month spend + per-day average), `GET /api/v1/ai/usage` (daily/monthly token usage and estimated cost breakdown).

6. **Approval workflow** — ActionProposal model with TTL (5 min default, configurable in AIConfig). Proposals persisted to `ai_action_proposals` table (survive restarts; expired proposals cleaned on startup). ActionExecutor with pre-execution re-check gate: (a) strategy exists in expected state, (b) market regime unchanged since proposal, (c) account equity within 5% of proposal time, (d) no circuit breaker active. Routes proposals through Risk Manager (param changes) and Orchestrator (allocation/suspend/resume). `POST /api/v1/ai/actions/{id}/approve` and `POST /api/v1/ai/actions/{id}/reject`. ApprovalRequested/Granted/Denied events on Event Bus. Full audit logging. Re-check failure returns explanation to chat.

7. **AI content generation** — DailySummaryGenerator with explicit data assembly: today's trades (entries, exits, P&L, R-multiples, hold durations), Orchestrator decisions (regime, allocations, suspensions), risk events (rejections, modifications, circuit breakers), performance context (daily/weekly targets, running stats), per-strategy breakdown (win rate, P&L, trade count). Dashboard insight endpoint (`GET /api/v1/ai/insight` with caching, demand-refreshed).

8. **Live Copilot UI** — Replace CopilotPlaceholder with full chat interface: MessageList with streaming token display via WebSocket, markdown rendering (react-markdown + remark-gfm + rehype-sanitize for XSS protection), message timestamps, copy-to-clipboard, ChatInput with send/cancel during stream, oldest-first message ordering. Bundle size delta from react-markdown checked after implementation (flag if >200KB gzipped).

9. **Copilot integration** — `useCopilotContext` hooks on all 7 pages providing page name, selected entity, and key visible data. Keyboard shortcut toggle. Conversation history loading with pagination. WebSocket reconnection strategy: on disconnect, re-fetch conversation from REST API, replace partial message with persisted version, reconnect WebSocket. Error and degraded states. Dev mode: "AI not configured" when no API key; simulated data note when dev mode with API key.

10. **Action card UI** — Inline action proposals in chat rendered from tool_use responses. Approve/Reject buttons. Visual states: pending (with countdown), expired, executed, failed. Approval confirmation dialog. Action result display in chat. Audio notification (configurable, default on) when proposals appear. Second audio alert when proposal has <1 min remaining before expiry.

11. **Dashboard AI insight card** — New card component, demand-refreshed (click or auto every 5 min during market hours), graceful "AI not available" state when service disabled.

12. **Debrief integration** — AI-generated daily summary view using DailySummaryGenerator output. Learning Journal conversation browser with pagination, date filtering, and tag filtering. Conversation detail view with full message history.

### Acceptance Criteria

1. **Claude API integration:**
   - ClaudeClient successfully calls Claude Opus and returns responses
   - tool_use definitions are included in all API calls; Claude can propose actions via tool_use
   - System starts and runs normally when ANTHROPIC_API_KEY is not set (AI disabled gracefully)
   - Rate limiting produces backoff behavior, not errors
   - API failures produce user-visible error messages, not crashes
   - System prompt includes ARGUS description, strategy summaries, and behavioral guardrails
   - System prompt instructs AI to never recommend specific trade entries/exits, always caveat uncertainty, reference actual data

2. **Tool definitions:**
   - 5 tools defined with complete JSON schemas
   - Each tool validates inputs against defined ranges (allocations 0–100%, risk params within sane bounds)
   - Unrecognized tool calls logged and treated as errors (no action card generated)
   - Tool definitions are testable independently of Claude API

3. **Chat persistence:**
   - Conversations survive page reload and server restart
   - Conversations keyed by calendar date with tag field
   - Message history loads with pagination (oldest-first in UI rendering)
   - Conversation list endpoint returns all conversations with metadata, filterable by date range and tag
   - UsageTracker records input_tokens, output_tokens, model, estimated_cost_usd for every API call
   - Usage endpoint returns accurate daily and monthly totals

4. **WebSocket streaming:**
   - Tokens appear in UI as generated (< 100ms latency per token after first)
   - Time-to-first-token < 3 seconds under normal API load
   - tool_use round-trips handled transparently — action proposals appear inline during stream
   - Stream cancellation works (client sends close frame, backend cancels Claude API call)
   - Connection interruption triggers reconnection: client re-fetches conversation from REST, replaces partial message, reconnects WS
   - Auth follows existing WS pattern (JWT in initial message)

5. **Context injection:**
   - Every page provides a context payload via `useCopilotContext`
   - AI responses demonstrate awareness of current page and visible data
   - Context includes: page name, selected entity (if any), key data visible on page
   - Total context payload stays within 2,000 token budget

6. **Approval workflow:**
   - AI proposes actions via tool_use; proposals render as action cards in chat
   - Proposals persisted to ai_action_proposals table (survive restart)
   - Proposals expire after TTL with visible "Expired" state and countdown
   - Approved actions pass 4-condition re-check before execution: strategy state valid, regime unchanged, equity within 5%, no circuit breaker
   - Re-check failure returns "Execution blocked — [reason]" to chat
   - Failed executions report back to chat with explanation
   - All approvals logged in audit trail
   - Audio notification on new proposal; second alert at <1 min remaining
   - Expired proposals cleaned on startup

7. **AI content:**
   - Daily summary generates a coherent narrative from explicitly assembled data (trades, orchestrator decisions, risk events, performance, per-strategy breakdown)
   - Dashboard insight card shows a relevant, non-generic insight
   - Both gracefully show "not available" when AI is disabled

8. **Cost tracking:**
   - Token usage tracked for every API call in ai_usage table
   - `GET /api/v1/ai/usage` returns daily and monthly totals with cost estimates
   - `GET /api/v1/ai/status` includes current-month spend and per-day average

9. **Regression:**
   - All 1,754 pytest + 296 Vitest tests pass
   - No strategy behavior changes
   - No existing API endpoint changes
   - All pages render correctly with AI disabled (identical to pre-Sprint 22)
   - Existing WebSocket (`/ws/v1/live`) unaffected

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Time-to-first-token (streaming) | < 3 seconds | Manual timing during paper session |
| Token display latency | < 100ms per token | Visual assessment of streaming smoothness |
| Conversation list load (50+ convos) | < 200ms | API response time |
| Message history load (50 msgs) | < 300ms | API response time |
| Dashboard insight refresh | < 5 seconds | Manual timing |
| Daily summary generation | < 15 seconds | API response time |
| System startup with AI disabled | No measurable difference | Compare startup times |
| tool_use round-trip (proposal creation) | < 500ms server-side | Log timing in ActionManager |
| Usage endpoint response | < 100ms | API response time |

## Dependencies
- Sprint 21.7 complete (it is — FMP Scanner merged)
- `anthropic` Python SDK installable via pip
- `react-markdown` + `remark-gfm` + `rehype-sanitize` installable via npm
- ANTHROPIC_API_KEY available as environment variable for testing (can test with mock when unavailable)
- Existing aiosqlite DB infrastructure operational
- Existing CopilotPanel shell (Sprint 21d, DEC-212) in place
- Existing WebSocket infrastructure (`/ws/v1/live`) for pattern reference
- Existing approval events defined in `argus/core/events.py`

## Relevant Decisions
- DEC-098: Claude Opus for all API calls — cost is trivial relative to trading capital
- DEC-170: Contextual AI Copilot — Claude on every page, slide-out panel, context injection, action capabilities, Learning Journal persistence
- DEC-212: Copilot shell architecture — separate component from SlideInPanel, own Zustand store, page context indicator
- DEC-217: Copilot button positioning — desktop bottom-right, mobile above watchlist FAB
- DEC-265 (revised): WebSocket for AI chat streaming, not SSE
- DEC-266 (revised): Calendar-date keying with optional tag field
- DEC-271 (new): Claude tool_use for structured action proposals
- DEC-272 (new): 5-type closed action enumeration for MVP
- DEC-273 (new): System prompt template with token budgets and behavioral guardrails
- DEC-274 (new): Per-call cost tracking from day one

## Relevant Risks
- RSK-NEW-1: Claude API dependency — Anthropic outage during trading session makes AI features unavailable. Mitigation: all AI features degrade gracefully; trading engine operates independently.
- RSK-NEW-2: API cost overrun — excessive chat during volatile sessions could exceed budget. Mitigation: rate limiting, response caching, cost tracking from day one with usage endpoint.
- RSK-NEW-3: Stale approval execution — market moves between proposal and approval. Mitigation: 5-minute TTL, 4-condition pre-execution re-check, DB-persisted proposals.
- RSK-NEW-4: tool_use hallucination — Claude calls tools with invalid parameters or fabricates action proposals. Mitigation: strict schema validation, sane range bounds, audit logging.
- RSK-NEW-5: aiosqlite write contention — AI writes (conversations, messages, proposals, usage) share SQLite write lock with Trade Logger. Mitigation: monitor during paper trading; if latency spikes, consider WAL mode or separate DB file.

## Session Count Estimate
9 sessions estimated (decomposed from original 6 to prevent compaction risk). Five backend sessions build the AI module, persistence, streaming, and approval workflow. Four frontend sessions activate the Copilot UI, integrate context hooks, build action cards, and wire Dashboard/Debrief. Sessions 2, 3, and 4 split into a/b pairs after compaction risk assessment. Each session scoped to complete comfortably within Claude Code's context window.
