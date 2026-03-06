# Tier 2 Review: Sprint 22, Session 4a — Copilot Core Chat

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    sprint-22-package/prompts/review-context.md

## Tier 1 Close-Out Report

[PASTE SESSION 4A CLOSE-OUT REPORT HERE]

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
