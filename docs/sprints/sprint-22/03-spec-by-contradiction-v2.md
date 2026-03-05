# Sprint 22: What This Sprint Does NOT Do

## Out of Scope

1. **NLP catalyst pipeline**: No SEC EDGAR integration, no FMP news feed analysis, no catalyst classification. Deferred to Sprint 23 (DEC-164). The AI Layer built here is the infrastructure that Sprint 23's NLP pipeline will use — including the tool_use mechanism.

2. **Setup quality scoring**: No 0–100 quality scores, no quality grade badges, no quality-based position sizing. Deferred to Sprint 24 (DEC-239). The approval workflow built here is the mechanism Sprint 24's dynamic sizer will use for human-in-the-loop adjustment.

3. **Multi-modal support**: No image input (charts, screenshots) to the AI. Text-only conversations. Image analysis would require additional API cost and context window budget.

4. **Voice input**: No speech-to-text for the Copilot. Text input only.

5. **Custom prompt engineering UI**: No UI for editing system prompts or prompt templates. Prompts are managed in code (`argus/ai/prompts.py`). A prompt management UI is a post-Phase 5 consideration.

6. **AI-initiated conversations**: The AI never initiates contact. All conversations start with a user message. Proactive alerts (e.g., "I notice unusual volume on NVDA") are a Sprint 23+ feature tied to the Universe Manager.

7. **Backtesting integration**: The AI cannot trigger or reference backtests. No "run a backtest on these parameters" action. Deferred to Sprint 29+ (BacktestEngine).

8. **Multi-user support**: Single operator. No conversation isolation between users. The existing JWT auth model (single password) applies to AI endpoints identically.

9. **Conversation branching/editing**: No editing sent messages, no branching conversations. Linear chat only.

10. **annotate_trade action**: No trade annotation via approval workflow. Low value for MVP. Deferred post-Sprint 22.

11. **manual_rebalance action**: No manual rebalance trigger via approval workflow. High-risk action with unclear approval UX. Deferred post-Sprint 22.

12. **Extended tool_use capabilities**: No tools beyond the 5 defined types (DEC-272). No tools for querying data, running calculations, or executing arbitrary code. The AI provides analysis via natural language; only the 5 defined action types are executable.

## Edge Cases to Reject

1. **Concurrent proposals for same action type**: Second proposal supersedes first (with "Previous proposal superseded" notice in chat). Do NOT queue multiple proposals of the same type.

2. **Approval of expired proposal**: Return error "Proposal expired" with 410 Gone status. Do NOT extend TTL or allow late approval.

3. **Chat while system is shutting down**: Return 503 Service Unavailable. Do NOT queue messages for delivery after restart.

4. **Message with empty content**: Reject client-side. Do NOT send empty messages to Claude API.

5. **Extremely long user messages (>10,000 chars)**: Truncate with notice. Do NOT send unbounded content to API.

6. **Conversation history exceeding token budget**: Truncate oldest messages. Keep system prompt + page context + last N messages within the 8,000-token history budget. Do NOT fail or omit system context to fit more history.

7. **tool_use with invalid parameters**: Validate against schema. Return tool_result with error message. Do NOT create ActionProposal. Do NOT crash.

8. **Unrecognized tool calls from Claude**: Log the call. Return tool_result with "Unrecognized tool" error. Do NOT create ActionProposal. Treat as plain text conversation.

9. **Pre-execution re-check failure**: Mark proposal as "Execution blocked — [reason]". Return explanation to chat. Do NOT retry execution. Do NOT extend TTL.

10. **WebSocket disconnect during active stream**: Backend cancels the Claude API call. Partial response is persisted as-is (marked incomplete). Client re-fetches from REST on reconnect.

11. **Allocation override exceeding 100% total**: Validate that proposed allocation + all other strategy allocations ≤ 100%. Reject via tool_result error if exceeded.

## Scope Boundaries

- Do NOT modify: `argus/strategies/` (any file — strategies must produce identical signals)
- Do NOT modify: `argus/core/orchestrator.py` core allocation logic (approval workflow CALLS orchestrator methods but does not change them)
- Do NOT modify: `argus/core/risk_manager.py` core gating logic (approval workflow CALLS risk manager methods but does not change them)
- Do NOT modify: `argus/execution/` (broker, order manager — no changes to execution path)
- Do NOT modify: `argus/data/` (data service, scanner, indicators — no changes to data pipeline)
- Do NOT modify: `argus/backtest/` (no backtesting changes)
- Do NOT modify: `argus/core/event_bus.py` internals (use existing publish/subscribe, add no new event delivery mechanisms)
- Do NOT modify: existing API route signatures in `argus/api/routes/` (only ADD new routes in `ai.py`)
- Do NOT modify: `argus/core/events.py` existing event classes (ApprovalRequested/Granted/Denied already exist and are sufficient)
- Do NOT modify: existing WebSocket handler at `/ws/v1/live` (new AI chat is a separate WebSocket endpoint `/ws/v1/ai/chat`)
- Do NOT optimize: prompt token usage. Use clear, verbose prompts. Optimize for quality, not cost. Per DEC-098, cost is trivial.
- Do NOT add: new Command Center pages. All AI UI lives in existing pages (Copilot panel, Dashboard card, Debrief views).
- Do NOT add: SSE endpoints. Streaming is via WebSocket only (DEC-265 revised).

## Interaction Boundaries

- This sprint does NOT change the behavior of: Event Bus delivery, strategy signal generation, Risk Manager gating decisions, Orchestrator allocation math, Order Manager execution, Trade Logger persistence, existing WebSocket real-time events (`/ws/v1/live`).
- This sprint does NOT affect: any component's behavior when ANTHROPIC_API_KEY is unset. The system must operate identically to pre-Sprint 22 when AI is disabled.

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| NLP catalyst classification | Sprint 23 | DEC-164 |
| Universe Manager broad monitoring | Sprint 23 | DEC-263 |
| Setup quality scoring (0–100) | Sprint 24 | DEC-239 |
| Dynamic position sizing | Sprint 24 | DEC-239 |
| AI-initiated proactive alerts | Sprint 23+ | — |
| Extended tool_use capabilities | Unscheduled | — |
| Prompt management UI | Post-Phase 5 | — |
| Multi-modal (image) support | Unscheduled | — |
| Backtest triggering from Copilot | Sprint 29+ | — |
| Conversation export/sharing | Unscheduled | — |
| Trade annotation action | Unscheduled | — |
| Manual rebalance action | Unscheduled | — |
