# Sprint 24.1, Session 3: TypeScript Build Fixes

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/tsconfig.app.json` — compiler options and strict mode settings
   - `argus/ui/src/api/types.ts` — Trade and StrategyInfo interfaces
   - Run `cd argus/ui && npx tsc --noEmit -p tsconfig.app.json 2>&1` to see the exact error list
2. Run the test baseline:
   ```
   cd argus/ui && npm test -- --run
   ```
   Expected: ~497 tests, all passing
3. Verify you are on branch `sprint-24.1`

## Objective
Fix all 22 pre-existing TypeScript strict-mode errors so `tsc --noEmit` exits with 0 errors. These are type-checking errors that don't affect Vite/esbuild runtime but indicate type safety gaps.

## Requirements

Fix the errors by category. The exact errors (as of Sprint 24 close) are:

### Category 1: CardHeaderProps missing `icon` prop (4 errors)
Files: `src/components/CatalystAlertPanel.tsx`, `src/features/dashboard/AIInsightCard.tsx` (×3)

The `<CardHeader>` component is being passed an `icon` prop that doesn't exist on `CardHeaderProps`. Options (choose the cleanest):
- If CardHeader is a local component (in `src/components/ui/`): add `icon` to its props interface
- If CardHeader is from shadcn: create a local wrapper or extend the type
- If `icon` is being passed but not used: remove it from the JSX

Investigate the CardHeader component first to understand the correct fix.

### Category 2: `child.props` unknown — React.Children typing (4 errors)
Files: `src/features/copilot/ChatMessage.tsx` (×2), `src/features/copilot/StreamingMessage.tsx` (×2)

These use `React.Children.map()` where `child.props` is typed as `unknown`. Fix by casting children to `React.ReactElement`:
```typescript
React.Children.map(children, (child) => {
  if (!React.isValidElement(child)) return child;
  // child is now React.ReactElement, child.props is accessible
  ...
})
```

### Category 3: Unused variables — TS6133 (3 errors)
Files: `src/features/copilot/CopilotPanel.tsx` (`pageKey`), `src/features/debrief/journal/ConversationBrowser.tsx` (`EASE`), `src/features/dashboard/PositionDetailPanel.tsx` (`entryPrice`)

Either remove the unused declarations or prefix with `_` if they're intentionally reserved.

### Category 4: Missing JSX namespace (1 error)
File: `src/features/copilot/TickerText.tsx`

Add explicit JSX namespace reference. Options:
- Change return type to `React.JSX.Element` or `React.ReactNode`
- Add `import type { JSX } from 'react'` if needed

### Category 5: StrategyInfo missing fields (3 errors)
File: `src/pages/PatternLibraryPage.tsx`

The code accesses `strategy.live_metrics` and `strategy.backtest_metrics` which don't exist on `StrategyInfo`. The type has `performance_summary` and `backtest_summary` instead.

Options:
- If the API actually returns `live_metrics`/`backtest_metrics`: add to the StrategyInfo interface in `types.ts`
- If the code should use `performance_summary`/`backtest_summary`: fix the property names in PatternLibraryPage
- Check the API response shape in `argus/api/routes/strategies.py` to determine which is correct

### Category 6: Trade type field mismatch (2 errors)
File: `src/pages/TradesPage.tsx`

The code uses `trade.realized_pnl` and `trade.outcome` which don't match the `Trade` interface. The interface has `pnl_dollars` (not `realized_pnl`). For `outcome`, check if it should be added to the Trade interface or if the code should derive outcome from pnl_dollars.

Check `argus/api/routes/trades.py` to verify what the API actually returns.

## Constraints
- Do NOT change runtime behavior — these are type annotation fixes only
- Do NOT enable additional strict flags in tsconfig
- Do NOT refactor surrounding code beyond the minimum needed to fix the type error
- Do NOT fix any issues that aren't in the 22 pre-existing errors (document any new errors you find)
- Do NOT modify backend Python files

## Test Targets
After implementation:
- `npx tsc --noEmit -p tsconfig.app.json` exits with 0 errors
- `npm test -- --run` — all Vitest tests pass (no runtime changes)
- No new tests to write (validation is the tsc exit code)
- Test command: `cd argus/ui && npx tsc --noEmit -p tsconfig.app.json && npm test -- --run`

## Definition of Done
- [ ] `tsc --noEmit` exits 0 (zero TypeScript errors)
- [ ] All Vitest tests pass
- [ ] No runtime behavior changes
- [ ] Close-out documents each fix category and approach taken
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Zero TS errors | `cd argus/ui && npx tsc --noEmit -p tsconfig.app.json` exits 0 |
| Vitest passes | `cd argus/ui && npm test -- --run` — all pass, same count |
| No runtime changes | Diff shows only type annotations, casts, imports, unused var removal |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file:**
`docs/sprints/sprint-24.1/session-3-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-24.1/review-context.md`
2. The close-out report path: `docs/sprints/sprint-24.1/session-3-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped — non-final session):
   ```
   cd argus/ui && npx tsc --noEmit -p tsconfig.app.json && npm test -- --run
   ```
5. Files that should NOT have been modified:
   - Any Python files
   - `argus/ui/tsconfig.app.json`
   - `argus/ui/package.json`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-24.1/session-3-review.md`

## Session-Specific Review Focus (for @reviewer)
1. **Zero TS errors:** Run `npx tsc --noEmit -p tsconfig.app.json` and verify exit code 0.
2. **No runtime changes:** Verify all changes are type-level only: annotations, casts, imports, unused variable removal. No logic changes.
3. **CardHeader fix approach:** Check which approach was used for the `icon` prop issue. If a shared component type was modified, verify it doesn't break other consumers.
4. **React.Children typing:** Verify the fix uses `React.isValidElement()` guard, not bare `as` cast.
5. **StrategyInfo type correctness:** If fields were added to the interface, verify they match the API response.
6. **Trade type fix:** Verify the fix maps to what the API actually returns.
7. **No new errors introduced:** Confirm error count went from 22 to 0.

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
1. Vitest tests fail after type fixes (runtime behavior changed)

### Warning (Proceed with caution, document)
2. More than 22 errors found — fix only original 22, document extras
3. CardHeaderProps fix requires changing shared component used in >5 files — use local type override instead
