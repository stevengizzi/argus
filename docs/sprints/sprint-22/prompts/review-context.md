# Sprint 22: Review Context

> This file is read by Claude Code during every Tier 2 review session.
> It contains the Sprint Spec, Specification by Contradiction, Regression Checklist,
> and Escalation Criteria. Session-specific review scope and focus are in the
> individual review prompt files.

---

## Review Instructions

You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any files.

Follow the review skill in .claude/skills/review.md.

---

## Sprint Spec

# Sprint 22: AI Layer MVP + Copilot Activation

### Goal
Activate the AI Layer — connect the Copilot shell (built Sprint 21d) to Claude API with streaming responses via WebSocket, persistent conversation history, page-aware context injection across all 7 Command Center pages, and a full approval workflow for AI-proposed actions using Claude's native tool_use API. Add AI-generated daily summaries to the Debrief and an AI insight card to the Dashboard. Track all API costs from day one. This is the sprint that makes ARGUS intelligent.

### Scope

#### Deliverables

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

#### Acceptance Criteria

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

#### Performance Benchmarks

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

### Relevant Decisions
- DEC-098: Claude Opus for all API calls
- DEC-170: Contextual AI Copilot — full scope
- DEC-212: Copilot shell architecture
- DEC-217: Copilot button positioning
- DEC-265 (revised): WebSocket for AI chat streaming, not SSE
- DEC-266 (revised): Calendar-date keying with optional tag field
- DEC-271 (new): Claude tool_use for structured action proposals
- DEC-272 (new): 5-type closed action enumeration for MVP
- DEC-273 (new): System prompt template with token budgets and behavioral guardrails
- DEC-274 (new): Per-call cost tracking from day one

### Relevant Risks
- RSK-NEW-1: Claude API dependency — graceful degradation
- RSK-NEW-2: API cost overrun — rate limiting, caching, usage tracking
- RSK-NEW-3: Stale approval execution — TTL + 4-condition re-check
- RSK-NEW-4: tool_use hallucination — schema validation, range bounds, audit logging
- RSK-NEW-5: aiosqlite write contention — monitor during paper trading

---

## Specification by Contradiction

# Sprint 22: What This Sprint Does NOT Do

### Out of Scope

1. **NLP catalyst pipeline**: No SEC EDGAR integration, no FMP news feed analysis, no catalyst classification. Deferred to Sprint 23 (DEC-164). The AI Layer built here is the infrastructure that Sprint 23's NLP pipeline will use — including the tool_use mechanism.

2. **Setup quality scoring**: No 0–100 quality scores, no quality grade badges, no quality-based position sizing. Deferred to Sprint 24 (DEC-239).

3. **Multi-modal support**: No image input (charts, screenshots) to the AI. Text-only conversations.

4. **Voice input**: No speech-to-text for the Copilot. Text input only.

5. **Custom prompt engineering UI**: No UI for editing system prompts or prompt templates. Prompts are managed in code (`argus/ai/prompts.py`).

6. **AI-initiated conversations**: The AI never initiates contact. All conversations start with a user message.

7. **Backtesting integration**: The AI cannot trigger or reference backtests. No "run a backtest on these parameters" action.

8. **Multi-user support**: Single operator. The existing JWT auth model applies to AI endpoints identically.

9. **Conversation branching/editing**: No editing sent messages, no branching conversations. Linear chat only.

10. **annotate_trade action**: No trade annotation via approval workflow. Deferred post-Sprint 22.

11. **manual_rebalance action**: No manual rebalance trigger via approval workflow. Deferred post-Sprint 22.

12. **Extended tool_use capabilities**: No tools beyond the 5 defined types (DEC-272). No tools for querying data, running calculations, or executing arbitrary code.

### Edge Cases to Reject

1. **Concurrent proposals for same action type**: Second proposal supersedes first (with "Previous proposal superseded" notice in chat). Do NOT queue.

2. **Approval of expired proposal**: Return error "Proposal expired" with 410 Gone status. Do NOT extend TTL.

3. **Chat while system is shutting down**: Return 503 Service Unavailable. Do NOT queue.

4. **Message with empty content**: Reject client-side. Do NOT send empty messages to Claude API.

5. **Extremely long user messages (>10,000 chars)**: Truncate with notice. Do NOT send unbounded content to API.

6. **Conversation history exceeding token budget**: Truncate oldest messages. Keep system prompt + page context + last N messages within 8,000-token history budget. Do NOT fail or omit system context to fit more history.

7. **tool_use with invalid parameters**: Validate against schema. Return tool_result with error message. Do NOT create ActionProposal.

8. **Unrecognized tool calls from Claude**: Log the call. Return tool_result with "Unrecognized tool" error. Do NOT create ActionProposal.

9. **Pre-execution re-check failure**: Mark proposal as "Execution blocked — [reason]". Return explanation to chat. Do NOT retry.

10. **WebSocket disconnect during active stream**: Backend cancels Claude API call. Partial response persisted as-is (marked incomplete). Client re-fetches from REST on reconnect.

11. **Allocation override exceeding 100% total**: Validate that proposed allocation + all other strategy allocations ≤ 100%. Reject via tool_result error if exceeded.

### Scope Boundaries

- Do NOT modify: `argus/strategies/` (any file — strategies must produce identical signals)
- Do NOT modify: `argus/core/orchestrator.py` core allocation logic (approval workflow CALLS orchestrator methods but does not change them)
- Do NOT modify: `argus/core/risk_manager.py` core gating logic (approval workflow CALLS risk manager methods but does not change them)
- Do NOT modify: `argus/execution/` (broker, order manager)
- Do NOT modify: `argus/data/` (data service, scanner, indicators)
- Do NOT modify: `argus/backtest/` (no backtesting changes)
- Do NOT modify: `argus/core/event_bus.py` internals (use existing publish/subscribe)
- Do NOT modify: existing API route signatures in `argus/api/routes/` (only ADD new routes in `ai.py`)
- Do NOT modify: `argus/core/events.py` existing event classes
- Do NOT modify: existing WebSocket handler at `/ws/v1/live`
- Do NOT optimize: prompt token usage. Use clear, verbose prompts. Per DEC-098, cost is trivial.
- Do NOT add: new Command Center pages.
- Do NOT add: SSE endpoints. Streaming is via WebSocket only (DEC-265 revised).

### Interaction Boundaries

- This sprint does NOT change the behavior of: Event Bus delivery, strategy signal generation, Risk Manager gating decisions, Orchestrator allocation math, Order Manager execution, Trade Logger persistence, existing WebSocket real-time events (`/ws/v1/live`).
- This sprint does NOT affect: any component's behavior when ANTHROPIC_API_KEY is unset. The system must operate identically to pre-Sprint 22 when AI is disabled.

---

## Sprint-Level Escalation Criteria

Trigger a Tier 3 review if ANY of the following occur:

1. **Trading safety breach**: Any code path where AI output could modify strategy signals, bypass Risk Manager gating, or alter execution without explicit human approval.
2. **Approval workflow bypass**: Any scenario where an action executes without passing through the approve endpoint and 4-condition re-check gate.
3. **File scope violation**: Any modification to files in `argus/strategies/`, `argus/core/orchestrator.py` (core logic), `argus/core/risk_manager.py` (core logic), `argus/execution/`, `argus/data/`, `argus/backtest/`, `argus/core/event_bus.py`, or existing API route signatures.
4. **Existing WebSocket disruption**: Any change to `/ws/v1/live` behavior or connection handling.
5. **tool_use false positive**: Claude's tool_use produces an ActionProposal that was not intentionally requested by the operator, and the validation layer fails to catch it.
6. **Memory/resource leak**: WebSocket streaming handler or Claude API client shows evidence of resource leak under sustained use.
7. **AI hallucination in data**: AI-generated content includes fabricated trade data, positions, or P&L figures not present in the actual database.
8. **Performance degradation**: Any existing endpoint's response time increases by >50% after AI module integration, OR existing test suite runtime increases by >20%.
9. **Cost anomaly**: Token usage per conversation significantly exceeds estimates (>3x budgeted token counts).
10. **Graceful degradation failure**: System behavior changes in ANY way when ANTHROPIC_API_KEY is unset compared to pre-Sprint 22 baseline.
11. **Authentication gap**: Any AI endpoint (REST or WebSocket) accessible without valid JWT.
12. **Event schema conflict**: New AI events conflict with or alter behavior of existing Event Bus subscribers.

---

## Sprint-Level Regression Checklist

After each session, verify ALL of the following. Any failure is a blocking issue.

| # | Check | How to Verify |
|---|-------|---------------|
| R1 | All existing pytest pass | `cd /path/to/argus && python -m pytest tests/ -x -q` — expect ≥1,754 passing |
| R2 | All existing Vitest pass | `cd argus/ui && npx vitest run` — expect ≥296 passing |
| R3 | Strategy signal purity | Grep `argus/strategies/` in `git diff` — must be empty. No strategy files modified. |
| R4 | Core orchestrator unchanged | Grep `argus/core/orchestrator.py` in `git diff` — empty or import-only. |
| R5 | Core risk manager unchanged | Grep `argus/core/risk_manager.py` in `git diff` — empty or import-only. |
| R6 | Execution path unchanged | Grep `argus/execution/` in `git diff` — must be empty. |
| R7 | Data pipeline unchanged | Grep `argus/data/` in `git diff` — must be empty. |
| R8 | Event Bus internals unchanged | Grep `argus/core/event_bus.py` in `git diff` — must be empty. |
| R9 | Existing API signatures preserved | No existing route has changed method, path, request body, or response schema. New routes only in `ai.py`. |
| R10 | Existing WebSocket unchanged | `argus/api/ws/` — existing live WS handler untouched. New `ai_chat.py` is additive only. |
| R11 | JWT auth on all new endpoints | Every new REST endpoint requires valid JWT. New WebSocket requires JWT in initial message. Verify with missing/invalid token → 401/403. |
| R12 | Graceful AI-disabled mode | Unset ANTHROPIC_API_KEY, start system. Verify: Dashboard renders (insight card shows "AI not available"), Debrief renders (journal shows empty state), Copilot shows "AI not configured", all non-AI endpoints work normally. |
| R13 | No import side effects | `python -c "from argus.ai import ClaudeClient"` succeeds with no API key |
| R14 | Config backward compat | System starts with existing config YAML that has no `ai:` section (defaults applied, AI disabled). |
| R15 | DB backward compat | System starts with existing DB that lacks ai_* tables (tables created on startup, no migration errors). |
