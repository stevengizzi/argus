# Tier 2 Review: Sprint 22, Session 4b — Copilot Integration

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    sprint-22-package/prompts/review-context.md

## Tier 1 Close-Out Report

[PASTE SESSION 4B CLOSE-OUT REPORT HERE]

## Review Scope
- Diff: `git diff HEAD~1 -- argus/ui/src/hooks/ argus/ui/src/pages/ argus/ui/src/features/copilot/`
- New files: useCopilotContext.ts, per-page context providers
- Modified: All 7 page components (minimal — hook call only), CopilotPanel (history, reconnection)
- NOT modified: existing stores (other than copilotUI), existing non-copilot components
- Test command: `cd argus/ui && npx vitest run`

## Session-Specific Review Focus
1. Verify useCopilotContext hook integrated on ALL 7 pages (not just some)
2. Verify page component modifications are minimal (import + single hook call)
3. Verify keyboard shortcut Cmd/Ctrl+K does not conflict with existing shortcuts (check DEC-199)
4. Verify WebSocket reconnection logic: disconnect → REST re-fetch → replace partial → reconnect
5. Verify conversation history pagination in code
6. Verify error state handling: 503, WS failure, rate limit
7. Check page diffs are truly minimal — `git diff` on each page file should show only the hook addition

## Visual Review

The developer should visually verify the following in a browser:

**1. Page context in header:** Navigate to each of the 7 pages with the Copilot panel open. The panel header should update to show the current page name (e.g., "ARGUS Copilot · Dashboard", "ARGUS Copilot · Trades", etc.). Verify all 7:
- Dashboard
- Trades
- Performance
- Orchestrator
- Pattern Library
- Debrief
- System

**2. Keyboard shortcut:** Press Cmd+K (Mac) or Ctrl+K. Copilot panel should toggle open. Press again — should toggle closed. Verify this works on at least 2 different pages. Verify it does NOT conflict with any existing keyboard shortcut (e.g., browser search bar should not also open).

**3. Conversation history:** Open Copilot. If there are previous conversations, verify a way to access them (dropdown, button, or similar). If no previous conversations exist, verify there's no broken UI element (empty list is fine, broken spinner is not).

**4. Reconnection banner:** (If testable) Stop the backend while the Copilot panel is open and a WebSocket connection is active. Verify a "Reconnecting..." or "Connection lost" banner appears in the panel — not a blank crash, not a silent failure. Restart the backend — verify the banner dismisses and connection re-establishes.

**5. All pages still render correctly:** Navigate to all 7 pages. Each should render without console errors, without layout changes, without missing content. The hook addition should be invisible to the user.

Verification conditions:
- Items 1–3, 5: backend running with API key set
- Item 4: requires stopping/starting backend mid-session

## Additional Context
- Implementation prompt: `sprint-22-package/prompts/s4b-impl.md`
- This session touches all 7 page components. The diffs should be minimal (1–2 lines each). If any page has a large diff, that's a flag.
