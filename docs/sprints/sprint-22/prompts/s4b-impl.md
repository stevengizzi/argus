# Sprint 22, Session 4b: Copilot Integration

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/ui/src/features/copilot/CopilotPanel.tsx` (Session 4a)
   - `argus/ui/src/stores/copilotUI.ts` (Session 4a)
   - `argus/ui/src/features/copilot/` (all Session 4a files)
   - `argus/ui/src/pages/` (all 7 page components — to add context hooks)
   - `argus/ai/context.py` (Session 1 — per-page context schemas)
2. Run: `cd argus/ui && npx vitest run`
   Expected: ≥302 tests (296 + Session 4a), all passing
3. Run: `python -m pytest tests/ -x -q`
   Expected: ≥1,809 tests, all passing
4. Verify branch: `sprint-22-ai-layer`

## Objective
Add page-aware context injection to the Copilot by implementing `useCopilotContext` hooks on all 7 pages. Add keyboard shortcut, conversation history loading with pagination, WebSocket reconnection strategy, and error/degraded state handling.

## Requirements

1. **Create `useCopilotContext` hook** (`argus/ui/src/hooks/useCopilotContext.ts`):
   - Generic hook that each page calls with its context data
   - Signature: `useCopilotContext(page: string, contextData: () => Record<string, any>)`
   - The hook registers the context provider with the copilot store
   - Context is lazily evaluated (function called only when sending a message)
   - When the user sends a message, the copilot store calls the registered context provider to get current page context
   - Returns: `{ page: string }` (for display in CopilotPanel header)

2. **Add context hooks to all 7 pages:**
   - **Dashboard** (`DashboardPage`): portfolio summary (equity, daily P&L, positions count), regime classification, active strategy count, any alerts
   - **Trades** (`TradesPage`): active filters, visible trade count, selected trade (if any) with entry/exit/P&L
   - **Performance** (`PerformancePage`): selected timeframe, key metrics (total return, Sharpe, win rate, max drawdown), selected strategy filter
   - **Orchestrator** (`OrchestratorPage`): strategy allocations table, current regime, schedule state, any suspended strategies
   - **Pattern Library** (`PatternLibraryPage`): selected pattern name, pattern stats (win rate, avg R, sample size)
   - **Debrief** (`DebriefPage`): current view (summary/journal), selected date, selected conversation (if any)
   - **System** (`SystemPage`): connection states (Databento, IBKR, API), system uptime, config summary
   - Each hook call is a single line addition per page component. Minimal invasion.

3. **Update CopilotPanel to display page context:**
   - Show current page name in header: "ARGUS Copilot • Dashboard" / "ARGUS Copilot • Trades" etc.
   - When sending message, include `page` and `pageContext` from the registered hook

4. **Keyboard shortcut:**
   - `Cmd+K` (Mac) / `Ctrl+K` (Windows/Linux) toggles Copilot panel
   - Register globally (not per-page)
   - Does not conflict with existing shortcuts (check DEC-199 for existing shortcuts)

5. **Conversation history:**
   - On CopilotPanel mount (first open): load today's conversation via `fetchConversation` or `get_or_create_today`
   - "Previous conversations" dropdown/button at top of message list
   - Loads conversation list via `fetchConversations` with pagination
   - Clicking a conversation loads its messages
   - Pagination: "Load more" button, 20 conversations per page
   - Date filtering in conversation list (optional — basic date range)

6. **WebSocket reconnection strategy (per S4 resolution):**
   - On unexpected WebSocket disconnect:
     a. Show "Reconnecting..." banner in CopilotPanel
     b. Re-fetch current conversation from REST API (`GET /api/v1/ai/conversations/{id}`)
     c. Replace any partial/streaming message with the persisted version from REST
     d. Attempt WebSocket reconnect with exponential backoff (1s, 2s, 4s, max 3 attempts)
     e. On successful reconnect: dismiss banner, re-auth
     f. On all retries failed: show "Connection lost. Click to retry." banner
   - Clean disconnect (user closes panel): no reconnect attempt

7. **Error and degraded states:**
   - AI service unavailable (503 from status): "AI service is currently unavailable. Trading continues normally." in panel
   - WebSocket connection failed: reconnection flow above
   - API error during chat: error banner with message, dismissible, chat input re-enabled
   - Rate limited: "Rate limited. Please wait a moment." message, auto-retry after delay

## Constraints
- Do NOT modify: any backend files
- Do NOT modify: page component structure or layout. Only ADD the useCopilotContext hook call to each page.
- Do NOT modify: existing keyboard shortcuts (DEC-199)
- Do NOT modify: existing stores other than copilotUI
- Minimize the diff in each page file — ideally a single import + single hook call

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `argus/ui/src/hooks/__tests__/useCopilotContext.test.ts`: hook registers context, returns page name, context function called on demand
  - `argus/ui/src/features/copilot/__tests__/CopilotIntegration.test.tsx`: keyboard shortcut toggles panel, conversation history loads, reconnection flow (mock WS disconnect → REST fetch → reconnect)
- Minimum new test count: 6
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] useCopilotContext hook implemented and integrated on all 7 pages
- [ ] Page name visible in Copilot header
- [ ] Keyboard shortcut toggles panel (Cmd/Ctrl+K)
- [ ] Conversation history loads with pagination
- [ ] WebSocket reconnection with REST re-fetch
- [ ] Error/degraded state handling (503, WS failure, rate limit)
- [ ] All existing tests pass
- [ ] ≥6 new Vitest tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All 7 pages render | Navigate to each page — no console errors |
| Existing shortcuts work | Test existing keyboard shortcuts per DEC-199 |
| Page component diffs minimal | `git diff argus/ui/src/pages/` — only import + hook lines added |
| Panel animation preserved | Open/close still animated |
| All existing tests pass | `cd argus/ui && npx vitest run` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
[See 06-regression-checklist.md]

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
[See 05-escalation-criteria.md]
