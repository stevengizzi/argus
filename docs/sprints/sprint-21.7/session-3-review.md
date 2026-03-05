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
