# Sprint 22, Session 4a: Copilot Core Chat

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/ui/src/features/copilot/CopilotPanel.tsx` (existing placeholder)
   - `argus/ui/src/stores/copilotUI.ts` (existing store)
   - `argus/ui/src/api/` (existing API client patterns)
   - `argus/ui/src/features/copilot/` (all existing copilot files)
   - `argus/api/routes/ai.py` (Session 2b — API contract)
   - `argus/api/ws/ai_chat.py` (Session 2b — WS message format)
2. Run the test suite: `cd argus/ui && npx vitest run`
   Expected: ≥296 tests, all passing
3. Run backend tests: `python -m pytest tests/ -x -q`
   Expected: ≥1,809 tests (previous + Session 3b), all passing
4. Verify you are on the correct branch: `sprint-22-ai-layer`
5. Install new npm dependencies: `cd argus/ui && npm install react-markdown remark-gfm rehype-sanitize`

## Objective
Rewrite the CopilotPanel from its placeholder state to a live chat interface. Build the message display, WebSocket streaming integration, markdown rendering (with XSS protection), and chat input with send/cancel.

## Requirements

1. **Install and verify dependencies:**
   - `react-markdown` (markdown rendering)
   - `remark-gfm` (GitHub Flavored Markdown — tables, strikethrough, etc.)
   - `rehype-sanitize` (XSS protection — prevents script injection in rendered markdown)
   - After install, check bundle size impact: `cd argus/ui && npx vite build && ls -la dist/assets/`. Note the total JS bundle size. Flag in close-out if react-markdown + deps add >200KB gzipped.

2. **Expand the copilot store** (`argus/ui/src/stores/copilotUI.ts`):
   - Add state:
     - `messages: ChatMessage[]` — current conversation messages
     - `conversationId: string | null`
     - `isStreaming: boolean`
     - `streamingContent: string` — accumulating content during stream
     - `wsConnected: boolean`
     - `aiEnabled: boolean` — from status endpoint
     - `error: string | null`
   - Add actions:
     - `sendMessage(content: string, page: string, pageContext: object)`
     - `cancelStream()`
     - `loadConversation(conversationId: string)`
     - `clearError()`
   - `ChatMessage` type:
     ```typescript
     interface ChatMessage {
       id: string;
       role: 'user' | 'assistant';
       content: string;
       toolUse?: ToolUseData[];
       isComplete: boolean;
       createdAt: string;
     }
     interface ToolUseData {
       toolName: string;
       toolInput: Record<string, any>;
       proposalId: string | null;
     }
     ```

3. **Create copilot API client** (new file in `argus/ui/src/api/` or `argus/ui/src/features/copilot/api.ts`):
   - REST methods:
     - `fetchConversations(params)` → GET /api/v1/ai/conversations
     - `fetchConversation(id)` → GET /api/v1/ai/conversations/{id}
     - `fetchAIStatus()` → GET /api/v1/ai/status
     - `sendChatMessage(body)` → POST /api/v1/ai/chat (non-streaming fallback)
   - WebSocket manager:
     - `connectChat(token: string)` → connects to WS /ws/v1/ai/chat
     - Sends auth message on connect
     - Dispatches events to store: `onToken`, `onToolUse`, `onStreamEnd`, `onError`
     - `sendMessage(msg)` — sends chat message via WS
     - `cancelStream()` — sends cancel via WS
     - `disconnect()`
     - Auto-reconnect on unexpected close (exponential backoff, max 3 retries)

4. **Create ChatMessage component** (`argus/ui/src/features/copilot/ChatMessage.tsx`):
   - Renders a single message (user or assistant)
   - User messages: simple text with right-aligned bubble style
   - Assistant messages: markdown-rendered with `react-markdown` + `remark-gfm` + `rehype-sanitize`
   - Supports code blocks with syntax highlighting (basic — monospace + background)
   - Timestamp display (relative: "2m ago", "1h ago")
   - Copy-to-clipboard button on hover for assistant messages
   - If message has `toolUse` data: render placeholder "[Action proposal]" (Session 5 builds ActionCard)

5. **Create StreamingMessage component** (`argus/ui/src/features/copilot/StreamingMessage.tsx`):
   - Renders the in-progress streaming response
   - Uses `streamingContent` from store
   - Renders with react-markdown (same as ChatMessage)
   - Shows blinking cursor at end during stream
   - Transitions to final ChatMessage when `stream_end` received

6. **Create ChatInput component** (`argus/ui/src/features/copilot/ChatInput.tsx`):
   - Text area input (auto-grows, max 5 lines, then scrolls)
   - Send button (or Enter key; Shift+Enter for newline)
   - When `isStreaming`: show Cancel button instead of Send
   - Cancel sends `cancelStream()` action
   - Disabled when `aiEnabled` is false (show "AI not configured" placeholder text)
   - Disabled when sending / waiting for WS auth
   - Empty message rejected client-side (no API call)
   - Max message length: 10,000 chars (truncate with notice)

7. **Rewrite CopilotPanel** (`argus/ui/src/features/copilot/CopilotPanel.tsx`):
   - Replace CopilotPlaceholder content with:
     - Header: "ARGUS Copilot" + status indicator (green dot when connected, gray when disconnected, red on error)
     - MessageList: scrollable container of ChatMessage components, oldest-first
     - StreamingMessage (when isStreaming)
     - ChatInput at bottom
     - Auto-scroll to bottom on new messages
   - Maintain existing slide-in/out animation and panel dimensions (DEC-212)
   - On panel open: connect WebSocket if not connected, load today's conversation
   - On panel close: keep WS connected (messages can arrive while closed)
   - Error state: banner at top with error message + dismiss
   - Loading state: skeleton while loading conversation history
   - Empty state: "Start a conversation with ARGUS Copilot" message

8. **Dev mode handling:**
   - When `aiEnabled` is false (no API key): show "AI Not Configured" state permanently in CopilotPanel. ChatInput disabled. No WebSocket connection attempted.
   - Check `aiEnabled` via status endpoint on mount.

## Constraints
- Do NOT modify: any files outside `argus/ui/src/features/copilot/`, `argus/ui/src/stores/copilotUI.ts`, and the new API client file
- Do NOT modify: existing pages, existing components, existing stores (other than copilotUI)
- Do NOT modify: any backend files
- PRESERVE: CopilotPanel open/close animation, panel dimensions, button positioning (DEC-212, DEC-217)
- Messages must render oldest-first (standard chat UI convention)
- Use only Tailwind utility classes for styling (no custom CSS)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `argus/ui/src/features/copilot/__tests__/ChatMessage.test.tsx`: renders user message, renders assistant message with markdown, handles code blocks, copy button appears on hover, renders tool_use placeholder
  - `argus/ui/src/features/copilot/__tests__/ChatInput.test.tsx`: sends message on Enter, Shift+Enter creates newline, shows Cancel when streaming, disabled when AI not configured, rejects empty message
  - `argus/ui/src/stores/__tests__/copilotUI.test.ts`: store state transitions (sendMessage → isStreaming, onToken → content accumulates, onStreamEnd → message added)
- Minimum new test count: 6
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] CopilotPanel shows live chat interface (not placeholder)
- [ ] Messages render with markdown (code blocks, tables, bold, lists)
- [ ] XSS protection via rehype-sanitize
- [ ] Streaming tokens display in real-time via WebSocket
- [ ] Send/Cancel works
- [ ] Panel animation preserved
- [ ] AI-disabled state shows "AI Not Configured"
- [ ] Messages ordered oldest-first
- [ ] Bundle size impact noted in close-out
- [ ] All existing tests pass
- [ ] ≥6 new Vitest tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Panel animation preserved | Open/close Copilot — animation identical to pre-sprint |
| Button positioning unchanged | Desktop: bottom-right. Mobile: above watchlist FAB |
| No page modifications | `git diff argus/ui/src/pages/` — empty |
| Dashboard still renders | Load Dashboard — no errors in console |
| All existing tests pass | `cd argus/ui && npx vitest run` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

Include in close-out: bundle size delta from react-markdown installation.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
[See 06-regression-checklist.md]

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
[See 05-escalation-criteria.md]
