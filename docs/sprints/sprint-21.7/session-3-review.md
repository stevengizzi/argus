# Tier 2 Review: Sprint 21.7, Session 3

## Instructions
READ-ONLY. Follow .claude/skills/review.md. Visual verification required.

## Sprint Spec (Session Scope)
PreMarketLayout.tsx: RankedWatchlistPlaceholder replaced with
PreMarketWatchlistPanel showing live watchlist data from useWatchlist() hook.

## Specification by Contradiction
- Must NOT modify WatchlistSidebar.tsx or WatchlistItem.tsx
- Must NOT add Catalyst or Quality columns
- Must NOT create new API endpoints or hooks

## [PASTE CLOSE-OUT REPORT HERE]
---BEGIN-CLOSE-OUT---

**Session:** Sprint 21.7, Session 3 — Pre-Market Watchlist Panel (Frontend)
**Date:** 2026-03-05
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/ui/src/features/dashboard/PreMarketLayout.tsx | modified | Added PreMarketWatchlistPanel component, imported Skeleton and useWatchlist, replaced RankedWatchlistPlaceholder usages, updated docstring |
| argus/ui/src/features/dashboard/PreMarketLayout.test.tsx | modified | Added useWatchlist mock with factory function, updated existing tests for new title, added 5 new PreMarketWatchlistPanel tests |

### Judgment Calls
Decisions made during implementation that were NOT specified in the prompt:
- **formatReason regex patterns**: Implemented regex to parse `gap_up_3.2%` and `gap_down_1.8%` patterns into compact `↑ 3.2%` / `↓ 1.8%` display. Spec showed examples but not exact parsing logic.
- **Skeleton row count**: Used 5 skeleton rows for loading state (spec said "5 skeleton rows" explicitly, so this aligns).
- **fmp_fallback treated as FMP**: Included `fmp_fallback` scan_source as triggering the green FMP badge, since it's still FMP-sourced data.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Create PreMarketWatchlistPanel component | DONE | PreMarketLayout.tsx:68-176 |
| Card with CardHeader "Pre-Market Watchlist" | DONE | PreMarketLayout.tsx:152-157 |
| Source badge (FMP green / Static neutral) | DONE | PreMarketLayout.tsx:71-74, 156 |
| Table columns: # / Symbol / Gap% / Reason | DONE | PreMarketLayout.tsx:163-168 |
| Gap% colored (green/red/dim) | DONE | PreMarketLayout.tsx:88-93, 118 |
| Reason formatted compact | DONE | PreMarketLayout.tsx:76-86 |
| Loading state: 5 skeleton rows | DONE | PreMarketLayout.tsx:95-111 |
| Empty state message | DONE | PreMarketLayout.tsx:125-132 |
| Replace RankedWatchlistPlaceholder | DONE | PreMarketLayout.tsx:239, 282 |
| Add useWatchlist import | DONE | PreMarketLayout.tsx:25 |
| 5 new Vitest tests | DONE | PreMarketLayout.test.tsx:152-264 |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| WatchlistSidebar unchanged | PASS | git diff shows no changes |
| PreMarketLayout other cards intact | PASS | SessionSummaryCard, GoalTracker, RegimeForecastPlaceholder, CatalystSummaryPlaceholder all present |
| DashboardPage renders correctly | PASS | All tests pass, no type errors |

### Test Results
- Tests run: 296
- Tests passed: 296
- Tests failed: 0
- New tests added: 5
- Command used: `cd argus/ui && npx vitest run`

### Unfinished Work
None

### Notes for Reviewer
- **Screenshot description**: The Pre-Market Watchlist panel renders as a Card with dark background, showing the "PRE-MARKET WATCHLIST" title in uppercase dim text with a green "FMP" badge (or neutral "Static" badge) to the right. Below the header is a 4-column table with headers "#", "Symbol", "Gap%", and "Reason" in dim text. Data rows show the rank number in dim, bold white symbol tickers (TSLA, NVDA), colored gap percentages (green "+3.2%", red "-1.8%"), and compact reason text ("↑ 3.2%", "↓ 1.8%"). Loading state shows 5 rows of shimmer skeleton animations. Empty state shows centered dim text "No symbols selected yet — scan runs before market open".

---END-CLOSE-OUT---

## Visual Verification Checklist
- [ ] PreMarketLayout shows "Pre-Market Watchlist" card (not placeholder)
- [ ] Source badge shows "FMP" (green/accent) or "Static" (neutral)
- [ ] Table shows: rank number, symbol, gap%, selection reason
- [ ] Gap% is green for positive, red for negative
- [ ] SessionSummaryCard, MarketCountdown, GoalTracker still visible on page
- [ ] No "Coming" badge on the Pre-Market Watchlist card
- [ ] Loading state shows skeleton rows (not empty card)

## Sprint-Level Regression Checklist
| Check | Verify |
|-------|--------|
| WatchlistSidebar unchanged | git diff WatchlistSidebar.tsx |
| Existing PreMarketLayout tests pass | npx vitest run PreMarketLayout |
| No new API routes added | git diff argus/api/ |
| React DOM structure consistent | no conditional skeleton/content swaps |

## Sprint-Level Escalation Criteria
- ESCALATE if: useWatchlist() replaced with a new hook/query
- ESCALATE if: WatchlistSidebar.tsx was modified
- ESCALATE if: Any strategy files modified

## Review Scope
- Diff: git diff HEAD~1
- Test command: npx vitest run
- Files that MUST NOT have been modified:
  WatchlistSidebar.tsx, WatchlistItem.tsx, useWatchlist.ts,
  any file in argus/strategies/, argus/core/
