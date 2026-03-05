# Sprint 22, Session 6: Dashboard AI Insight Card + Debrief Integration

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/ui/src/features/dashboard/` (existing Dashboard components)
   - `argus/ui/src/features/debrief/` (existing Debrief components)
   - `argus/api/routes/ai.py` (insight + conversations endpoints)
   - `argus/ai/summary.py` (Session 3b — DailySummaryGenerator)
   - `argus/ui/src/stores/` (existing store patterns)
   - `argus/ui/src/api/` (existing API client patterns)
2. Run: `cd argus/ui && npx vitest run`
   Expected: ≥312 tests (previous + Session 5), all passing
3. Run: `python -m pytest tests/ -x -q`
   Expected: ≥1,809 tests, all passing
4. Verify branch: `sprint-22-ai-layer`

## Objective
Add the AI insight card to the Dashboard page and integrate the Learning Journal conversation browser with daily summary view into the Debrief page.

## Requirements

1. **Dashboard AI Insight Card** (`argus/ui/src/features/dashboard/AIInsightCard.tsx`):
   - Compact card component matching existing Dashboard card style
   - Header: "AI Insight" with sparkle icon (✨ or lucide-react `Sparkles`)
   - Body: AI-generated text (2-3 sentences), rendered with react-markdown
   - Footer: "Generated [time]" timestamp + "Refresh" button
   - **Behavior:**
     - On mount: fetch insight via `GET /api/v1/ai/insight`
     - Auto-refresh: every 5 minutes during market hours (9:30 AM–4:00 PM ET). Use the server's `insight_refresh_interval_seconds` from status endpoint if available, else default 300s.
     - Manual refresh: click "Refresh" button
     - Loading state: subtle skeleton matching card dimensions
     - Error state: "Unable to generate insight" with retry button
     - AI disabled: "AI insights not available" — gray text, no refresh button
   - **Placement:** Add to Dashboard grid. Position: after portfolio summary, before trade activity. Match existing card dimensions and spacing.

2. **Debrief Daily Summary View:**
   - In the existing Debrief page, add a new section/tab: "AI Summary"
   - Content: the AI-generated daily summary for the selected date
   - Fetch via: call `POST /api/v1/ai/chat` with a message like "Generate daily summary for {date}" OR call a dedicated summary endpoint if one exists
   - If no summary exists for the date: "No AI summary available for this date. Generate one?" button
   - Rendered with react-markdown (same rendering pipeline as Copilot messages)
   - Matches existing Debrief section styling

3. **Learning Journal Conversation Browser** (`argus/ui/src/features/debrief/journal/ConversationBrowser.tsx`):
   - Component showing past AI conversations
   - **List view:**
     - Fetches conversations via `GET /api/v1/ai/conversations` with date range + tag filters
     - Each item shows: date, tag badge (color-coded: session=blue, research=purple, debrief=green, pre-market=amber, general=gray), title or first message preview, message count
     - Sorted newest-first
     - Pagination: "Load more" button (20 per page)
   - **Filters:**
     - Date range picker (or predefined: "Today", "This Week", "This Month", "All")
     - Tag filter: multi-select for tag types
   - **Detail view:**
     - Click a conversation → expand or navigate to full message history
     - Messages rendered same as Copilot (ChatMessage component reuse)
     - Read-only — no sending messages from here
     - Back button to return to list
   - **Placement:** New tab/section in Debrief page alongside existing content

4. **Debrief integration wiring:**
   - Add "Learning Journal" tab to Debrief page navigation (alongside existing tabs)
   - If Debrief has a tab system: add as new tab. If it uses sections: add as collapsible section.
   - READ the existing Debrief page structure carefully before deciding on integration approach.
   - Graceful empty state: "No conversations yet. Start chatting with the Copilot to build your Learning Journal." with link/button to open Copilot.

5. **API calls:**
   - Dashboard insight: TanStack Query hook `useAIInsight()` with `refetchInterval` during market hours
   - Conversations: TanStack Query hook `useConversations(filters)` with pagination
   - Conversation detail: TanStack Query hook `useConversation(id)`
   - All hooks return `{ data, isLoading, error, refetch }` following existing patterns

## Constraints
- Do NOT modify: any backend files
- Do NOT modify: existing Dashboard cards or their layout/behavior (only ADD the new card)
- Do NOT modify: existing Debrief content or sections (only ADD new section/tab)
- Do NOT modify: copilot components (reuse ChatMessage for read-only message display)
- Match existing styling patterns. Study existing cards and Debrief sections before building.

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `argus/ui/src/features/dashboard/__tests__/AIInsightCard.test.tsx`: renders insight text, shows loading skeleton, shows AI-disabled state, refresh button triggers fetch
  - `argus/ui/src/features/debrief/journal/__tests__/ConversationBrowser.test.tsx`: renders conversation list, filters by date/tag, pagination loads more, click opens detail view, empty state message
- Minimum new test count: 4
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] AIInsightCard renders on Dashboard with generated insight
- [ ] Insight auto-refreshes during market hours
- [ ] Insight card degrades gracefully when AI disabled
- [ ] Daily summary viewable in Debrief
- [ ] ConversationBrowser lists past conversations with filters
- [ ] Conversation detail view shows full message history
- [ ] Learning Journal accessible via Debrief navigation
- [ ] Empty states for all new components
- [ ] All existing tests pass
- [ ] ≥4 new Vitest tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Dashboard renders with AI disabled | Unset key, load Dashboard — insight card shows "not available", all other cards normal |
| Debrief renders with no conversations | Load Debrief — Learning Journal shows empty state, existing Debrief sections unchanged |
| Existing Dashboard cards unchanged | Compare visual before/after — no layout shifts |
| Existing Debrief content unchanged | Existing tabs/sections work identically |
| All existing tests pass | `cd argus/ui && npx vitest run` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

This is the FINAL session of Sprint 22. In the close-out, include a summary of all sessions and note any items that need follow-up.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
[See 06-regression-checklist.md]

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
[See 05-escalation-criteria.md]
