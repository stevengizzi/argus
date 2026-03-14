# Sprint 24, Session 11f: Visual-Review Fixes + Cleanup

## Pre-Flight Checks
1. Read: `argus/ui/src/features/debrief/QualityOutcomeScatter.tsx`, `argus/ui/src/pages/DebriefPage.tsx`, `argus/ui/src/features/dashboard/QualityDistributionCard.tsx`, `argus/ui/src/features/dashboard/SignalQualityPanel.tsx`
2. Scoped test: `cd argus/ui && npx vitest run`
3. Branch: `sprint-24`

## Objective
Visual verification of all quality UI with seeded data. Fix visual issues and clean up
LOW-severity findings from Sessions 9–11 reviews.

## Part 1: Seed Script for Visual Verification

Create `scripts/seed_quality_data.py` — a disposable script that:
1. Inserts 25–30 synthetic `quality_history` rows into argus.db covering:
   - All 8 grades (A+ through C), weighted toward B range
   - At least 3 different strategies (orb_breakout, vwap_reclaim, afternoon_momentum)
   - Mix of symbols (AAPL, TSLA, NVDA, META, MSFT, etc.)
   - Varied pattern_strength (20–95), quality_score (15–95), and component values
   - ~60% of rows with non-null outcome_realized_pnl and outcome_r_multiple
     (mix of winners and losers), rest null (open/pending)
   - Timestamps spread across today
2. Also inserts a matching `--cleanup` mode that deletes all seeded rows
   (use a recognizable marker, e.g., `signal_context LIKE '%seed_marker%'`)
3. Usage: `python scripts/seed_quality_data.py` to seed, `python scripts/seed_quality_data.py --cleanup` to remove

After seeding, boot the frontend (`npm run dev`) and visually verify ALL quality UI:

| Page | Component | What to Check |
|------|-----------|---------------|
| Dashboard | QualityDistributionCard | Donut chart shows grade distribution, center count |
| Dashboard | SignalQualityPanel | Histogram bars, passed/filtered counter |
| Orchestrator | RecentSignals | Signal rows with badges, strategy names, timestamps |
| Trades | Quality column | QualityBadge pills in table rows |
| Trades | TradeDetailPanel | Expanded quality section (if trade has quality data) |
| Performance | QualityGradeChart | Grouped bars by grade (avg PnL, win rate, avg R) |
| Debrief | QualityOutcomeScatter | Scatter dots with grade coloring, trend line |

Log any visual issues found. Fix them as Part 3 items.

## Part 2: Code Cleanup (from review findings)

### Fix A: Remove unused import
In `argus/ui/src/features/debrief/QualityOutcomeScatter.tsx`, remove the unused
`Line` import from recharts.

### Fix B: Update DebriefPage docstring
In `argus/ui/src/pages/DebriefPage.tsx`, update the file header docstring:
- "Five sections" → "Six sections"
- Add "Quality" to the section list
- Add 'q' to the keyboard shortcuts list

### Fix C: Extract shared grade constants
Create `argus/ui/src/constants/qualityConstants.ts` with:
- `GRADE_ORDER` — the 8-grade tuple (A+, A, A-, B+, B, B-, C+, C)
- `GRADE_COLORS` — grade-to-color mapping

Update imports in:
- `argus/ui/src/features/dashboard/QualityDistributionCard.tsx`
- `argus/ui/src/features/dashboard/SignalQualityPanel.tsx`
- Any other files that duplicate these constants (check QualityGradeChart, QualityOutcomeScatter)

Verify no test regressions after import changes.

## Part 3: Visual Fixes
Address any issues discovered during Part 1 visual verification. Typical fixes:
- Color adjustments, layout/spacing, responsive breakpoints
- Tooltip positioning, empty state text
- Chart axis labels, legend placement

If no visual issues are found, note "No visual fixes needed" in the close-out.

## Constraints
- Do not add new features
- Do not refactor working logic
- Seed script is disposable (not production code) — place in `scripts/`, do NOT
  add to outputs or commit to main. Include in commit for reproducibility but
  document it as a dev-only tool.
- Run `--cleanup` before committing to ensure no seed data in the DB

## Test Targets
- All existing 497 Vitest must pass after import refactor
- No new tests required (cleanup session)
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] Seed script created and working (seed + cleanup modes)
- [ ] All 7 quality UI touchpoints visually verified with seeded data
- [ ] Unused Line import removed
- [ ] DebriefPage docstring updated
- [ ] GRADE_COLORS/GRADE_ORDER extracted to shared constants
- [ ] All 497 Vitest pass
- [ ] Seed data cleaned up (--cleanup run before commit)
- [ ] Visual fixes applied (or "none needed" documented)

## Close-Out
Write report to `docs/sprints/sprint-24/session-11f-closeout.md`.