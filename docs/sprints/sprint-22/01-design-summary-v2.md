# Sprint 22 Design Summary (v2 — Post-Adversarial Review)

**Sprint Goal:** Activate the AI Layer MVP — connect the Copilot shell to Claude API with streaming responses via WebSocket, persistent conversation history, page-aware context injection, and a full approval workflow for AI-proposed actions using Claude's native tool_use. Add AI-generated daily summaries to the Debrief and an AI insight card to the Dashboard. Track all API costs from day one.

**Session Breakdown:**
- Session 1: Backend — AI Core (ClaudeClient with tool_use support, PromptManager with defined system prompt template and token budgets, SystemContextBuilder, AIConfig, ResponseCache, `argus/ai/` module)
- Session 2a: Backend — Chat persistence (DB schema: ai_conversations, ai_messages, ai_usage tables, ConversationManager with calendar-date keying and tags, UsageTracker)
- Session 2b: Backend — Chat API + WebSocket streaming (REST chat endpoints with auth, WS /ws/v1/ai/chat streaming with tool_use handling, usage endpoint, server lifecycle, AppState wiring)
- Session 3a: Backend — Approval workflow (ActionProposal model with DB persistence in ai_action_proposals, ActionManager lifecycle with TTL expiry, approve/reject API routes, Event Bus integration)
- Session 3b: Backend — Action executors + AI content (5 tool_use executors with validation + re-check logic, DailySummaryGenerator with explicit data assembly, Dashboard insight endpoint, AIService orchestration)
- Session 4a: Frontend — Copilot core chat (store expansion, API client, CopilotPanel rewrite, MessageList, ChatMessage with markdown + rehype-sanitize, StreamingMessage via WebSocket, ChatInput with send/cancel)
- Session 4b: Frontend — Copilot integration (useCopilotContext hooks on all 7 pages, keyboard shortcut, conversation history loading/pagination, WebSocket reconnection strategy, error/degraded states)
- Session 5: Frontend — Action cards + approval UX (inline action proposals from tool_use, Approve/Reject buttons, pending/expired/executed/failed states, audio notifications, expiry warnings, approval confirmation)
- Session 6: Frontend — Dashboard AI insight card + Debrief integration (insight card component, daily summary view, Learning Journal conversation browser with pagination and date/tag filtering)

**Key Decisions:**
- DEC-264: Full DEC-170 scope in Sprint 22. No phasing.
- DEC-265 (revised): WebSocket for AI chat streaming — reuses existing WS infrastructure, matches architecture doc, supports bidirectional (cancellation, future server-initiated messages). Endpoint: `WS /ws/v1/ai/chat`.
- DEC-266 (revised): Conversations keyed by calendar date (not trading day) with optional tag field ("pre-market", "session", "research", "debrief", "general"). Supports weekend research.
- DEC-267: Action proposal TTL 5 min (configurable). Proposals persisted to ai_action_proposals table (S2). Expired proposals cleaned on startup.
- DEC-268: Context injection via per-page useCopilotContext hooks. SystemContextBuilder combines page context with system state.
- DEC-269: AI insight card demand-refreshed (click or auto every 5 min during market hours). Cached response.
- DEC-270: Markdown rendering via react-markdown + remark-gfm + rehype-sanitize (XSS protection).
- DEC-271 (new): Claude tool_use for structured action proposals. Replaces fragile JSON-in-text parsing. Tools defined for each action type. Backend intercepts tool_use, creates ActionProposal, returns tool_result. Sprint 23 NLP pipeline will extend same mechanism.
- DEC-272 (new): Closed 5-type action enumeration: strategy_allocation_override, risk_param_update, strategy_suspend, strategy_resume, generate_report. Each with defined schema and validation. All others out of scope.
- DEC-273 (new): System prompt template — ARGUS description, operator context, strategy summaries, behavioral guardrails (advisory only, never recommend entries/exits, caveat uncertainty, reference actual data). Token budgets: system ≤1,500, page context ≤2,000, history ≤8,000, response ≤4,096.
- DEC-274 (new): Per-call cost tracking — ai_usage table (conversation_id, timestamp, input_tokens, output_tokens, model, estimated_cost_usd). GET /api/v1/ai/usage endpoint. From day one.

**Scope Boundaries:**
- IN: Claude API integration with tool_use (`argus/ai/`), Copilot chat via WebSocket, persistent conversations (calendar-date keyed with tags), page-aware context injection on all 7 pages, 5-type approval workflow with DB-persisted proposals, report generation, daily summary with explicit data assembly, Dashboard AI insight card, Debrief Learning Journal, per-call cost tracking, audio notifications for proposals, ~85 new tests
- OUT: NLP catalyst (Sprint 23), quality scoring (Sprint 24), strategy logic changes, Orchestrator algorithm changes, new pages, custom prompt UI, multi-modal, voice, annotate_trade action, manual_rebalance action

**Regression Invariants:**
- All existing 1,754 pytest + 296 Vitest tests pass
- All 4 strategies produce identical signals (AI layer is purely advisory)
- All existing API endpoints return identical responses
- WebSocket bridge (`/ws/v1/live`) delivers real-time events unchanged
- JWT auth gates all new and existing protected routes
- CopilotPanel open/close animation preserved
- All pages render correctly with AI disabled (ANTHROPIC_API_KEY unset)
- No performance degradation when AI service unavailable

**File Scope:**
- Create: `argus/ai/client.py`, `argus/ai/prompts.py`, `argus/ai/context.py`, `argus/ai/cache.py`, `argus/ai/conversations.py`, `argus/ai/actions.py`, `argus/ai/executors.py`, `argus/ai/summary.py`, `argus/ai/usage.py`, `argus/ai/config.py`, `argus/ai/tools.py` (tool_use definitions), `argus/api/routes/ai.py`, `argus/api/ws/ai_chat.py`, `argus/ui/src/features/copilot/ChatMessage.tsx`, `argus/ui/src/features/copilot/ChatInput.tsx`, `argus/ui/src/features/copilot/ActionCard.tsx`, `argus/ui/src/features/copilot/StreamingMessage.tsx`, `argus/ui/src/hooks/useCopilotContext.ts`, `argus/ui/src/features/dashboard/AIInsightCard.tsx`, `argus/ui/src/features/debrief/journal/ConversationBrowser.tsx`
- Modify: `argus/ai/__init__.py`, `argus/core/config.py`, `argus/api/dependencies.py`, `argus/api/server.py`, `argus/ui/src/features/copilot/CopilotPanel.tsx`, `argus/ui/src/stores/copilotUI.ts`, `argus/ui/src/features/dashboard/`, `argus/ui/src/features/debrief/`, config YAML files
- Do not modify: `argus/strategies/`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/`, `argus/data/`, `argus/backtest/`, `argus/core/event_bus.py`, existing API route signatures, `argus/core/events.py`

**Test Strategy:**
- ~85 new tests (65 pytest, 20 Vitest)
- Backend: ClaudeClient unit tests (mock API + tool_use), PromptManager template tests, SystemContextBuilder output tests, ConversationManager CRUD tests, UsageTracker tests, ActionProposal lifecycle tests (including DB persistence + expiry), tool_use parsing tests, executor validation tests, re-check logic tests, WebSocket streaming tests, API route tests
- Frontend: ChatMessage rendering, ActionCard states, useCopilotContext hooks, streaming display, notification trigger tests
- Integration: end-to-end chat flow with mocked Claude API (including tool_use round-trip), approval workflow full cycle
- All tests work with AI disabled

**Dependencies:**
- `anthropic` Python SDK (pip)
- `react-markdown` + `remark-gfm` + `rehype-sanitize` (npm)
- ANTHROPIC_API_KEY env var (or AI disabled)
- Sprint 21.7 complete (it is)
- Existing aiosqlite + WebSocket infrastructure

**Escalation Criteria:**
- Claude API integration produces unexpected behavior affecting trading decisions
- Approval workflow bypasses Risk Manager gates
- WebSocket streaming causes memory leaks or connection exhaustion
- AI-generated content contains hallucinated trade/position data
- Chat persistence degrades existing DB operations
- tool_use parsing produces false positive action proposals
- Cost tracking shows unexpected consumption patterns
- Any modification to files outside declared scope

**Doc Updates Needed:**
- `docs/architecture.md` — AI Layer section, WS endpoint, DB schema, tool_use architecture
- `docs/decision-log.md` — DEC-264 through DEC-274 (11 entries)
- `docs/dec-index.md` — new entries
- `docs/project-knowledge.md` — current state, sprint history, costs
- `CLAUDE.md` — active sprint, AI module, commands
- `docs/sprint-history.md` — Sprint 22 entry
- config YAMLs — `ai:` section
- `docs/live-operations.md` — ANTHROPIC_API_KEY requirement

**Artifacts to Generate:**
1. Sprint Spec (v2)
2. Specification by Contradiction (v2)
3. Session Breakdown
4. Implementation Prompt ×9
5. Review Prompt ×9
6. Sprint-Level Escalation Criteria
7. Sprint-Level Regression Checklist
8. Doc Update Checklist
