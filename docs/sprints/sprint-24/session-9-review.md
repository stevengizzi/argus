# Tier 2 Review: Sprint 24, Session 9

## Instructions
READ-ONLY review. Follow `.claude/skills/review.md`.
**Write report to:** `docs/sprints/sprint-24/session-9-review.md`

## Review Context
Read `docs/sprints/sprint-24/review-context.md`

## Tier 1 Close-Out Report
Read: `docs/sprints/sprint-24/session-9-closeout.md`

## Review Scope
- Diff: `git diff HEAD~1`
- Test command (non-final): `cd argus/ui && npx vitest run`
- Should NOT have been modified: existing Trades table columns (only new column added)

## Session-Specific Review Focus
1. Verify QualityBadge grade coloring: A range green, B range amber, C range red/gray
2. Verify tooltip contains grade, score, and risk tier text
3. Verify Trades table backward compatible — pre-Sprint-24 trades show "—"
4. Verify TanStack Query hooks follow existing patterns (staleTime, error handling)

## Visual Review
1. Trades table: Quality column with grade badges
2. QualityBadge colors match grade
3. Tooltip on hover
4. Empty state for old trades

