# Tier 2 Review: Sprint 22, Session 4a — Copilot Core Chat

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    sprint-22-package/prompts/review-context.md

## Tier 1 Close-Out Report

---BEGIN-CLOSE-OUT---

**Session:** Sprint 22.4a — Copilot Core Chat
**Date:** 2026-03-06
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/ui/package.json | modified | Added react-markdown, remark-gfm, rehype-sanitize, @testing-library/user-event |
| argus/ui/src/stores/copilotUI.ts | modified | Expanded store with chat state (messages, streaming, WS connection) |
| argus/ui/src/features/copilot/api.ts | added | REST API client + WebSocket manager for AI chat |
| argus/ui/src/features/copilot/ChatMessage.tsx | added | Message component with markdown rendering + XSS protection |
| argus/ui/src/features/copilot/StreamingMessage.tsx | added | Streaming response component with blinking cursor |
| argus/ui/src/features/copilot/ChatInput.tsx | added | Auto-growing textarea with send/cancel functionality |
| argus/ui/src/features/copilot/CopilotPanel.tsx | modified | Rewrote from placeholder to live chat interface |
| argus/ui/src/features/copilot/CopilotPanel.test.tsx | modified | Updated tests for new panel structure |
| argus/ui/src/features/copilot/index.ts | modified | Added exports for new components |
| argus/ui/src/features/copilot/__tests__/ChatMessage.test.tsx | added | 6 tests for ChatMessage component |
| argus/ui/src/features/copilot/__tests__/ChatInput.test.tsx | added | 7 tests for ChatInput component |
| argus/ui/src/stores/__tests__/copilotUI.test.ts | added | 8 tests for copilotUI store |

### Judgment Calls
- Added `@testing-library/user-event` as devDependency: Required for testing keyboard interactions (Enter/Shift+Enter) in ChatInput tests.
- Added `isLoading` state to store: Not explicitly specified but needed for loading skeleton UX.
- Used CSS animation for blinking cursor instead of JS interval: More performant, matches spec intent.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Install markdown dependencies | DONE | package.json |
| Expand copilot store | DONE | copilotUI.ts |
| Create copilot API client | DONE | api.ts |
| Create ChatMessage component | DONE | ChatMessage.tsx |
| Create StreamingMessage component | DONE | StreamingMessage.tsx |
| Create ChatInput component | DONE | ChatInput.tsx |
| Rewrite CopilotPanel | DONE | CopilotPanel.tsx |
| XSS protection via rehype-sanitize | DONE | ChatMessage.tsx, StreamingMessage.tsx |
| Messages ordered oldest-first | DONE | CopilotPanel.tsx MessageList |
| Panel animation preserved | DONE | Same animation code retained |
| AI-disabled state | DONE | AINotConfiguredState component |
| WebSocket auto-reconnect | DONE | api.ts CopilotWebSocketManager |
| ≥6 new tests | DONE | 21 new tests added |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Panel animation preserved | PASS | Same animation variants code retained |
| Button positioning unchanged | PASS | CopilotButton unchanged |
| No page modifications | PASS | `git diff argus/ui/src/pages/` is empty |
| Dashboard still renders | PASS | No changes to dashboard components |
| All existing tests pass | PASS | 319 tests passing |

### Test Results
- Tests run: 319
- Tests passed: 319
- Tests failed: 0
- New tests added: 23 (6 ChatMessage + 7 ChatInput + 8 store + 2 CopilotPanel)
- Command used: `cd argus/ui && npx vitest run`

### Bundle Size Impact
- Total JS bundle (gzipped): 438.75 KB
- react-markdown + remark-gfm + rehype-sanitize: ~30-50KB gzipped (well under 200KB threshold)
- Note: Pre-existing TypeScript error in PositionDetailPanel.tsx blocks `npm run build` but not vite build

### Unfinished Work
None

### Notes for Reviewer
- Pre-existing TypeScript error in `PositionDetailPanel.tsx:40` (unused `entryPrice` variable) blocks `npm run build` but is outside session scope. Vite build succeeds.
- WebSocket integration is complete but requires backend AI services to be enabled for full functionality.
- Tool use rendering shows placeholder "[Action proposal]" per spec — Session 5 builds ActionCard.

---END-CLOSE-OUT---

## Review Scope
- Diff: `git diff HEAD~1 -- argus/ui/src/features/copilot/ argus/ui/src/stores/copilotUI.ts argus/ui/src/api/`
- New files: ChatMessage.tsx, ChatInput.tsx, StreamingMessage.tsx, copilot API client
- Modified: CopilotPanel.tsx, copilotUI.ts store
- NOT modified: any page components, any other stores, any backend files
- Test command: `cd argus/ui && npx vitest run`

## Session-Specific Review Focus
1. Verify CopilotPanel replaces placeholder with live chat (not additive alongside placeholder)
2. Verify react-markdown + remark-gfm + rehype-sanitize all imported and used
3. Verify XSS protection via rehype-sanitize (not just react-markdown alone)
4. Verify messages render oldest-first
5. Verify WebSocket connects to `/ws/v1/ai/chat` (not SSE, not existing WS)
6. Verify AI-disabled state logic in code (input disabled, no WS connection attempted)
7. Verify panel animation preserved in code (same component structure, same Framer Motion config)
8. Check bundle size impact noted in close-out
9. Verify no page components modified

## Visual Review

The developer should visually verify the following in a browser:

**1. Panel open/close animation:** Click the Copilot button. Panel should slide in with the same animation as before Sprint 22. Close it — same animation out. No flicker, no layout jump.

**2. Empty state:** With no conversation history, the panel should show a welcome message (e.g., "Start a conversation with ARGUS Copilot") — not a blank panel, not an error, not a loading spinner that never resolves.

**3. AI-disabled state:** Unset ANTHROPIC_API_KEY, restart the backend. Open the Copilot panel. Verify:
- Shows "AI Not Configured" or equivalent — not an error message
- Chat input is visibly disabled (grayed out, cannot type)
- No console errors in browser dev tools

**4. Message rendering:** With backend running and API key set, send a test message. Verify:
- User message appears visually distinct from assistant messages (alignment, color, or style)
- Assistant response streams in token-by-token, not appearing all at once
- Blinking cursor visible at the end of the message during streaming
- Cursor disappears when stream completes
- Send a message like "Show me **bold**, `inline code`, a code block, and a bullet list" — verify each renders correctly (bold is bold, code is monospace with background, list has bullets)

**5. Copy button:** Hover over an assistant message. A copy-to-clipboard button should appear. Click it — verify the text copies correctly (paste somewhere to confirm).

**6. Send/Cancel:** Type a message, press Enter — message sends. While streaming, the Send button should change to Cancel. Click Cancel — streaming stops.

**7. Copilot button position:** Desktop: bottom-right of viewport.

Verification conditions:
- Items 1–2: backend running, no API key needed
- Item 3: backend running with ANTHROPIC_API_KEY unset
- Items 4–6: backend running with ANTHROPIC_API_KEY set
- Item 7: any state

## Additional Context
- Implementation prompt: `sprint-22-package/prompts/s4a-impl.md`
- This is the first frontend session. Backend Sessions 1–3b should be complete.
- Bundle size delta from react-markdown should be noted in the close-out.
