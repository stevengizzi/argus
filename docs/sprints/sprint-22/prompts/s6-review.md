# Tier 2 Review: Sprint 22, Session 6 — Dashboard AI Insight + Debrief Integration

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    docs/sprints/sprint-22/prompts/review-context.md

## Tier 1 Close-Out Report

[PASTE SESSION 6 CLOSE-OUT REPORT HERE]

## Review Scope
- Diff: `git diff HEAD~1 -- argus/ui/src/features/dashboard/ argus/ui/src/features/debrief/`
- New files: AIInsightCard.tsx, ConversationBrowser.tsx + sub-components
- Modified: Dashboard page (add insight card), Debrief page (add journal section)
- NOT modified: existing Dashboard cards, existing Debrief sections, backend files
- Test command: `cd argus/ui && npx vitest run`

## Session-Specific Review Focus
1. Verify insight card degrades gracefully: AI disabled → "not available", error → retry button
2. Verify auto-refresh only during market hours (not 24/7)
3. Verify existing Dashboard cards unaffected (no layout shifts, no behavior changes)
4. Verify ConversationBrowser has date and tag filtering
5. Verify conversation detail reuses ChatMessage component (not duplicate rendering)
6. Verify Debrief empty state when no conversations exist
7. Verify existing Debrief tabs/sections unchanged
8. **This is the final session.** Run the FULL regression checklist (R1–R15).
9. Verify total test count: ≥1,819 pytest + ≥316 Vitest (approximate targets)

## Additional Context
- Implementation prompt for this session: `docs/sprints/sprint-22/prompts/s6-impl.md`
