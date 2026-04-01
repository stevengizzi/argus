# Sprint 32.5, Session 7f: Experiments Dashboard Visual Review Fixes (Contingency)

> **This is a contingency session.** Use only if the S7 visual review or Tier 2
> review surfaced visual/UX issues. If S7 review was CLEAR with no visual issues,
> skip this session entirely.

## Pre-Flight Checks
1. Read the S7 review report: `docs/sprints/sprint-32.5/session-7-review.md`
2. Read the S7 close-out: `docs/sprints/sprint-32.5/session-7-closeout.md`
3. Identify specific visual/UX issues from the review
4. Run scoped tests: `cd argus/ui && npx vitest run`
5. Create working branch: `git checkout -b sprint-32.5-session-7f`

## Objective
Fix visual/UX issues discovered during S7 review. Scope limited to the Experiments Dashboard page. No new features.

## Constraints
- Do NOT add new features — fixes only
- Do NOT modify: any backend files, any other pages, navigation shortcuts
- Limit changes to Experiments page styling, layout, and display logic

## Test Targets
- All existing tests must still pass
- Add tests only if the fix changes component behavior
- Test command: `cd argus/ui && npx vitest run`

## Close-Out
Follow .claude/skills/close-out.md.
**Write to:** docs/sprints/sprint-32.5/session-7f-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-32.5/review-context.md`
2. Close-out: `docs/sprints/sprint-32.5/session-7f-closeout.md`
3. Diff: `git diff main...HEAD`
4. Test command: `cd argus/ui && npx vitest run`
5. Files NOT modified: backend files, other pages, navigation config

## Session-Specific Review Focus (for @reviewer)
1. Verify fixes address specific issues from S7 review
2. Verify no new features introduced
3. Verify existing pages unchanged

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Navigation and routing unchanged
- [ ] All Vitest pass
- [ ] Existing pages accessible

## Sprint-Level Escalation Criteria (for @reviewer)
Same as sprint-level criteria in review-context.md.
