# Sprint 23.5, Session 6f: Visual-Review Fixes (Contingency)

## Pre-Flight Checks
Before making any changes:
1. Read the S5 and S6 close-out reports — identify visual deviations noted
2. Read the S5 and S6 Tier 2 review reports — identify visual concerns flagged
3. Run the test suite: `cd argus/ui && npx vitest run` — all tests must pass
4. Run backend tests: `cd argus && python -m pytest tests/ -x -q` — all tests must pass

## Objective
Address visual deviations identified during S5 and S6 visual review. This session is contingency — it only runs if visual issues were found.

## Requirements

[TO BE FILLED FROM VISUAL REVIEW FINDINGS]

The developer or runner should populate this section with specific visual fixes needed based on the S5/S6 review:

1. [Visual deviation 1]: [Fix description]
2. [Visual deviation 2]: [Fix description]
...

## Constraints
- Only modify files created or modified in S5 and S6:
  - `argus/ui/src/hooks/useCatalysts.ts`
  - `argus/ui/src/components/CatalystBadge.tsx`
  - `argus/ui/src/components/CatalystAlertPanel.tsx`
  - `argus/ui/src/components/IntelligenceBriefView.tsx`
  - `argus/ui/src/components/BriefingCard.tsx`
  - `argus/ui/src/pages/DashboardPage.tsx`
  - `argus/ui/src/pages/OrchestratorPage.tsx`
  - `argus/ui/src/pages/DebriefPage.tsx`
- Do NOT modify any backend files
- Do NOT modify any other pages
- Do NOT add new components unless strictly necessary for a fix

## Visual Review
After fixes, re-verify all visual review items from S5 and S6:
1. Dashboard: catalyst badges correct placement, color, count
2. Orchestrator: alert panel scrolls, quality scores colored
3. Debrief: brief renders as markdown, date nav works, generate button works
4. All three pages: no layout regressions

## Test Targets
- All existing tests must pass
- Add tests only if fixes introduce new behavior (usually 0–2 new tests)

## Definition of Done
- [ ] All visual deviations from S5/S6 review addressed
- [ ] All tests pass
- [ ] Visual re-verification complete

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
R1–R25 from `docs/sprints/sprint-23.5/sprint-23.5-review-context.md`

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Items 1–15 from `docs/sprints/sprint-23.5/sprint-23.5-review-context.md`
