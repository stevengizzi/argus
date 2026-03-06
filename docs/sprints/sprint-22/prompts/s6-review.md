# Tier 2 Review: Sprint 22, Session 6 — Dashboard AI Insight + Debrief Integration

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    sprint-22-package/prompts/review-context.md

## Tier 1 Close-Out Report

[PASTE SESSION 6 CLOSE-OUT REPORT HERE]

## Review Scope
- Diff: `git diff HEAD~1 -- argus/ui/src/features/dashboard/ argus/ui/src/features/debrief/`
- New files: AIInsightCard.tsx, ConversationBrowser.tsx + sub-components
- Modified: Dashboard page (add insight card), Debrief page (add journal section)
- NOT modified: existing Dashboard cards, existing Debrief sections, backend files
- Test command: `cd argus/ui && npx vitest run`

## Session-Specific Review Focus
1. Verify insight card degrades gracefully in code: AI disabled → "not available", error → retry button
2. Verify auto-refresh logic only fires during market hours (not 24/7)
3. Verify existing Dashboard cards and layout untouched in diff
4. Verify ConversationBrowser has date and tag filtering in code
5. Verify conversation detail reuses ChatMessage component (not duplicate rendering logic)
6. Verify Debrief empty state when no conversations exist
7. Verify existing Debrief tabs/sections unchanged in diff
8. **This is the final session.** Run the FULL regression checklist (R1–R15).
9. Verify total test count: ≥1,819 pytest + ≥316 Vitest (approximate targets)

## Visual Review

The developer should visually verify the following in a browser:

**1. Dashboard — AI Insight Card (with AI enabled):**
- Navigate to Dashboard. A new "AI Insight" card should be visible.
- The card should show 2–3 sentences of AI-generated insight text, not placeholder or error.
- A "Refresh" button and a "Generated [time]" timestamp should be visible.
- Click Refresh — the insight should update (may take a few seconds).
- The card should fit naturally in the Dashboard grid — no overlapping with existing cards, no layout shifts, consistent sizing and spacing with neighbors.

**2. Dashboard — AI Insight Card (with AI disabled):**
- Unset ANTHROPIC_API_KEY, restart backend.
- Navigate to Dashboard. The insight card should show "AI insights not available" (or similar) in gray text. No Refresh button. No error. No console errors.
- All other Dashboard cards should render exactly as before — portfolio summary, positions, trade activity, etc. unchanged.

**3. Dashboard — existing cards unchanged:**
- With AI enabled, compare the Dashboard layout to pre-Sprint 22 (or mental model). Every existing card should be in the same position, same size, same content. The only addition is the new insight card.

**4. Debrief — Learning Journal tab/section:**
- Navigate to Debrief. A new "Learning Journal" tab or section should be visible in the page navigation.
- Click into it. If conversations exist: verify a list of conversations showing date, tag badge (color-coded), title/preview, and message count.
- If no conversations exist: verify a friendly empty state message like "No conversations yet. Start chatting with the Copilot to build your Learning Journal." — not a blank page, not an error.

**5. Debrief — conversation filtering:**
- If conversations exist: test the date filter (e.g., "Today", "This Week"). Verify the list updates.
- Test the tag filter (e.g., select only "session" tag). Verify filtering works.
- If pagination is relevant (20+ conversations): verify "Load more" works.

**6. Debrief — conversation detail:**
- Click on a conversation in the list. Verify it opens a detail view showing the full message history.
- Messages should render the same as in the Copilot panel (markdown, user/assistant styling). Verify they look consistent.
- This view should be read-only — no chat input, no send button.
- A back button or navigation should return to the conversation list.

**7. Debrief — daily summary:**
- If a daily summary has been generated: verify it appears in the Debrief under an "AI Summary" section/tab.
- The summary should render with markdown formatting (same pipeline as chat messages).
- If no summary exists for the selected date: verify a "No AI summary available" message or a "Generate" button — not a blank space.

**8. Debrief — existing content unchanged:**
- All existing Debrief sections/tabs (whatever was there before Sprint 22) should be unchanged — same content, same layout, same behavior.

Verification conditions:
- Items 1, 3, 4–8: backend running with ANTHROPIC_API_KEY set
- Item 2: backend running with ANTHROPIC_API_KEY unset
- Items 5–6: require at least 1–2 prior Copilot conversations to exist in the database
- Item 7: requires a daily summary to have been generated (via Copilot "generate daily summary" request or direct API call)

## Additional Context
- Implementation prompt: `sprint-22-package/prompts/s6-impl.md`
- This is the FINAL session of Sprint 22. The close-out should include a full sprint summary.
- After this review, proceed to Tier 3 architectural review for sprint completion.
