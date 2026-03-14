# Sprint 24.1, Session 4f: Visual Review Fixes (Contingency)

## Pre-Flight Checks
Before making any changes:
1. Read the close-out reports from Sessions 4a and 4b:
   - `docs/sprints/sprint-24.1/session-4a-closeout.md`
   - `docs/sprints/sprint-24.1/session-4b-closeout.md`
2. Read the visual review notes from the developer (will be provided below)
3. Run the scoped test baseline:
   ```
   cd argus/ui && npm test -- --run
   ```
   Expected: all passing
4. Verify you are on branch `sprint-24.1`
5. Confirm `tsc --noEmit` exits 0

## Objective
Fix visual issues discovered during Sessions 4a/4b visual review. This is a contingency session — if no issues were found, this session is unused.

## Requirements
[TO BE FILLED IN by the developer based on visual review findings]

The developer will paste specific visual issues here. Common patterns:
- Spacing/alignment inconsistencies
- Color mismatches with design system
- Responsive breakpoint issues
- Missing empty states
- Tooltip positioning problems
- Chart legend layout issues

## Constraints
- Do NOT modify: backend Python files
- Do NOT add: new features or components beyond fixing visual issues
- Do NOT change: data fetching, API calls, or component logic
- Keep fixes minimal and targeted

## Test Targets
- Vitest: all existing tests pass
- `tsc --noEmit` exits 0
- Test command: `cd argus/ui && npx tsc --noEmit -p tsconfig.app.json && npm test -- --run`

## Definition of Done
- [ ] All visual issues from review fixed
- [ ] Vitest passes
- [ ] `tsc --noEmit` exits 0
- [ ] Developer confirms visual review passes
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file:**
`docs/sprints/sprint-24.1/session-4f-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

This is the **final session** of the sprint. The close-out should run the full test suite:
```
python -m pytest -x -q -n auto
cd argus/ui && npx tsc --noEmit -p tsconfig.app.json && npm test -- --run
```

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-24.1/review-context.md`
2. The close-out report path: `docs/sprints/sprint-24.1/session-4f-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (**FINAL SESSION — full suite**):
   ```
   python -m pytest -x -q -n auto
   cd argus/ui && npx tsc --noEmit -p tsconfig.app.json && npm test -- --run
   ```
5. Files that should NOT have been modified:
   - Any Python files (frontend-only visual fix session)
   - Any files not identified in the visual review findings

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-24.1/session-4f-review.md`

## Session-Specific Review Focus (for @reviewer)
1. **Minimal changes:** This is a visual fix session. Changes should be CSS/layout/styling only.
2. **Visual issues resolved:** Cross-reference visual review findings from S4a/S4b with fixes applied.
3. **No scope creep:** No additional features or enhancements beyond specific visual issues.
4. **Full suite passes:** Both pytest and Vitest full suites pass. `tsc --noEmit` exits 0.
5. **Sprint-wide final check:** Verify all sprint deliverables are complete by reviewing the Sprint Spec deliverables list against cumulative changes.

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Order Manager position lifecycle unchanged
- [ ] TradeLogger handles quality-present and quality-absent trades
- [ ] Schema migration idempotent, no data loss
- [ ] Quality engine bypass path intact
- [ ] All pytest pass (full suite with `-n auto`)
- [ ] All Vitest pass
- [ ] TypeScript build clean (`tsc --noEmit` exits 0)
- [ ] API response shapes unchanged
- [ ] Frontend renders without console errors

## Sprint-Level Escalation Criteria (for @reviewer)
### Critical (Halt immediately)
1. Vitest tests fail after visual fixes

### Warning (Proceed with caution, document)
2. Visual issues require component restructuring — defer to future sprint
