# Tier 2 Review: Sprint 22, Session 5 — Action Cards + Approval UX

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    docs/sprints/sprint-22/prompts/review-context.md

## Tier 1 Close-Out Report

[PASTE SESSION 5 CLOSE-OUT REPORT HERE]

## Review Scope
- Diff: `git diff HEAD~1 -- argus/ui/src/features/copilot/ argus/ui/src/utils/`
- New files: ActionCard.tsx, notification utility
- Modified: ChatMessage.tsx (integrate ActionCard), copilotUI store (proposal state)
- NOT modified: any backend files, any non-copilot components
- Test command: `cd argus/ui && npx vitest run`

## Session-Specific Review Focus
1. Verify all 6 proposal states render correctly: pending, approved, executed, rejected, expired, failed
2. Verify approve flow includes confirmation dialog (not one-click execute)
3. Verify countdown timer updates live and shows expiry warning at <1 min
4. Verify audio notifications use Web Audio API (no external audio files)
5. Verify notification toggle exists and defaults to on
6. Verify audio is user-gesture-gated (Web Audio context creation)
7. Verify ActionCard replaces the "[Action proposal]" placeholder from Session 4a

## Additional Context
- Implementation prompt for this session: `docs/sprints/sprint-22/prompts/s5-impl.md`
