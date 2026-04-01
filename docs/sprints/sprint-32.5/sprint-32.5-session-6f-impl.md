# Sprint 32.5, Session 6f: Shadow Trades Visual Review Fixes (Contingency)

> **This is a contingency session.** Use only if the S6 visual review or Tier 2
> review surfaced visual/UX issues. If S6 review was CLEAR with no visual issues,
> skip this session entirely.

## Pre-Flight Checks
1. Read the S6 review report: `docs/sprints/sprint-32.5/session-6-review.md`
2. Read the S6 close-out: `docs/sprints/sprint-32.5/session-6-closeout.md`
3. Identify specific visual/UX issues from the review
4. Run scoped tests: `cd argus/ui && npx vitest run`
5. Verify branch: `main`

## Objective
Fix visual/UX issues discovered during S6 review. Scope limited to the Shadow Trades tab and related components. No new features.

## Constraints
- Do NOT add new features — fixes only
- Do NOT modify: any backend files, Live Trades tab, navigation/routing
- Do NOT modify: the ShadowTrades API hook (data layer) unless the fix requires a query param change
- Limit changes to component styling, layout, and display logic

## Test Targets
- All existing tests must still pass
- Add tests only if the fix changes component behavior (not just styling)
- Test command: `cd argus/ui && npx vitest run`

## Close-Out
Follow .claude/skills/close-out.md.
**Write to:** docs/sprints/sprint-32.5/session-6f-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-32.5/review-context.md`
2. Close-out: `docs/sprints/sprint-32.5/session-6f-closeout.md`
3. Diff: `git diff main...HEAD`
4. Test command: `cd argus/ui && npx vitest run`
5. Files NOT modified: backend files, Live Trades components, routing

## Session-Specific Review Focus (for @reviewer)
1. Verify fixes address the specific issues flagged in S6 review
2. Verify no new features introduced
3. Verify Live Trades tab still completely unchanged

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Trade Log live trades unchanged
- [ ] Navigation unchanged
- [ ] All Vitest pass

## Sprint-Level Escalation Criteria (for @reviewer)
Same as sprint-level criteria in review-context.md.
