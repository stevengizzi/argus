# Sprint 22: Session Breakdown

## Session Dependency Graph

```
S1 (AI Core) → S2a (Persistence) → S2b (API + WS) → S3a (Approval) → S3b (Executors + Content)
                                                                              ↓
S4a (Copilot Chat) → S4b (Integration) → S5 (Action Cards) → S6 (Dashboard + Debrief)
```

Sessions 1–3b are strictly sequential (each builds on the previous).
Session 4a can begin after Session 2b (needs API + WS endpoints).
Sessions 4b–6 are strictly sequential after 4a.
Session 5 requires Session 3b complete (needs action proposal data structures).

---

## Sessions

### Session 1: Backend — AI Core Module
**Scope:** Create `argus/ai/` module foundation: ClaudeClient, PromptManager, SystemContextBuilder, ResponseCache, AIConfig, tool definitions.
**Creates:** `argus/ai/__init__.py`, `client.py`, `prompts.py`, `context.py`, `cache.py`, `config.py`, `tools.py`
**Modifies:** `argus/core/config.py` (add AIConfig)
**Compaction Risk:** Medium-Low (7 new files but each is focused and self-contained)
**Tests:** ~12 new pytest

### Session 2a: Backend — Chat Persistence Layer
**Scope:** DB schema (ai_conversations, ai_messages, ai_usage), ConversationManager, UsageTracker.
**Creates:** `argus/ai/conversations.py`, `argus/ai/usage.py`
**Modifies:** DB initialization in `argus/analytics/trade_logger.py` or startup (table creation)
**Compaction Risk:** Low (CRUD + schema, well-bounded)
**Tests:** ~10 new pytest

### Session 2b: Backend — Chat API + WebSocket Streaming
**Scope:** REST endpoints, WebSocket chat handler with tool_use streaming, usage endpoint, server lifecycle integration, AppState wiring.
**Creates:** `argus/api/routes/ai.py`, `argus/api/ws/ai_chat.py`
**Modifies:** `argus/api/dependencies.py` (AppState), `argus/api/server.py` (lifecycle)
**Compaction Risk:** Medium (WebSocket + tool_use streaming is the most complex single piece)
**Tests:** ~10 new pytest

### Session 3a: Backend — Approval Workflow Skeleton
**Scope:** ActionProposal model, ai_action_proposals table, ActionManager lifecycle (create/approve/reject/expire), API routes, Event Bus integration, startup cleanup.
**Creates:** `argus/ai/actions.py`
**Modifies:** `argus/api/routes/ai.py` (add action routes), DB initialization (new table)
**Compaction Risk:** Medium-Low (well-defined state machine)
**Tests:** ~8 new pytest

### Session 3b: Backend — Action Executors + AI Content
**Scope:** 5 executor implementations with validation + 4-condition re-check, DailySummaryGenerator with explicit data assembly, Dashboard insight endpoint, AIService orchestration class.
**Creates:** `argus/ai/executors.py`, `argus/ai/summary.py`, `argus/ai/service.py`
**Modifies:** `argus/api/routes/ai.py` (insight endpoint), config YAMLs (`ai:` section)
**Compaction Risk:** Medium (5 executors + data assembly + validation, but each is small)
**Tests:** ~15 new pytest

### Session 4a: Frontend — Copilot Core Chat
**Scope:** Rewrite CopilotPanel from placeholder to live chat. Store expansion, API client module, MessageList, ChatMessage (markdown + rehype-sanitize), StreamingMessage (WebSocket), ChatInput (send/cancel).
**Creates:** `ChatMessage.tsx`, `ChatInput.tsx`, `StreamingMessage.tsx`, copilot API client
**Modifies:** `CopilotPanel.tsx`, `copilotUI.ts` store
**Compaction Risk:** Medium (significant UI rewrite, but well-bounded component tree)
**Tests:** ~6 new Vitest
**Notes:** Check bundle size delta from react-markdown. Messages render oldest-first. Dev mode shows "AI not configured" when no key.

### Session 4b: Frontend — Copilot Integration
**Scope:** useCopilotContext hooks on all 7 pages, keyboard shortcut, conversation history loading/pagination, WebSocket reconnection, error/degraded states.
**Creates:** `useCopilotContext.ts` hook file, per-page context providers
**Modifies:** All 7 page components (add context hook), `CopilotPanel.tsx` (history + reconnection)
**Compaction Risk:** Medium (touches 7+ files but each change is small — hook integration)
**Tests:** ~6 new Vitest

### Session 5: Frontend — Action Cards + Approval UX
**Scope:** ActionCard component from tool_use data, Approve/Reject flow, visual states (pending/countdown/expired/executed/failed), confirmation dialog, audio notifications, expiry warning.
**Creates:** `ActionCard.tsx`, notification audio utility
**Modifies:** `CopilotPanel.tsx` / message rendering (integrate action cards), copilot store (action state)
**Compaction Risk:** Medium-Low (single component + integration points)
**Tests:** ~4 new Vitest
**Dependency:** Requires Session 3b complete (action proposal data structure)

### Session 6: Frontend — Dashboard AI Insight + Debrief Integration
**Scope:** AIInsightCard component, Debrief daily summary view, Learning Journal ConversationBrowser with pagination + date/tag filtering, conversation detail view.
**Creates:** `AIInsightCard.tsx`, `ConversationBrowser.tsx`, journal sub-components
**Modifies:** Dashboard page (add insight card), Debrief page (add journal section)
**Compaction Risk:** Medium-Low (two independent integration points)
**Tests:** ~4 new Vitest

---

## Total Test Target
~85 new tests (65 pytest + 20 Vitest)
