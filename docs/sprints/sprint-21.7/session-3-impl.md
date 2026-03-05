# Sprint 21.7, Session 3: Pre-Market Watchlist Panel (Frontend)

## Pre-Flight Checks
Before making any changes:
1. Read these files:
   - argus/ui/src/features/dashboard/PreMarketLayout.tsx
   - argus/ui/src/features/watchlist/WatchlistItem.tsx
   - argus/ui/src/hooks/useWatchlist.ts
   - argus/ui/src/api/types.ts (confirm scan_source + selection_reason added)
   - argus/ui/src/components/Card.tsx, CardHeader.tsx, Badge.tsx (existing components)
2. Run: cd argus/ui && npx vitest run
   Expected: 291 tests, all passing
3. Confirm Session 2 is complete (types.ts already updated with new fields).

## Objective
Replace the RankedWatchlistPlaceholder in PreMarketLayout.tsx with a live
PreMarketWatchlistPanel that shows FMP-selected symbols with gap%, source
badge, and selection reason. Uses existing useWatchlist() hook — no new API.

## Requirements

### 1. Create new component: PreMarketWatchlistPanel

Add as a local component in PreMarketLayout.tsx (no new file needed — keep
co-located with PreMarketLayout since it's only used here).
```tsx
function PreMarketWatchlistPanel() {
  const { data, isLoading, isError } = useWatchlist();

  // Loading state: skeleton rows
  // Error state: brief error message
  // Empty state: "No symbols selected yet — scan runs before market open"
  // Data state: table of watchlist items
}
```

Visual spec:
- Card component wrapping, same as other PreMarketLayout cards
- CardHeader with title "Pre-Market Watchlist" + source badge (see below)
- Source badge in header: if any item has scan_source="fmp" → show
  "FMP" badge in green/accent. If scan_source="static" or empty →
  show "Static" badge in neutral/dim color.
- Table columns: # | Symbol | Gap% | Reason
  - # : rank (1, 2, 3, ...)
  - Symbol: bold ticker text
  - Gap%: colored number (green for gap_up, red for gap_down, dim for high_volume)
  - Reason: compact text showing selection_reason
    e.g., "↑ 3.2%" or "↓ 1.8%" or "Vol" (abbreviated)
- 5–15 rows expected
- Loading state: 5 skeleton rows in the table
- Empty state: centered "—" text with explanation

### 2. Replace RankedWatchlistPlaceholder in PreMarketLayout.tsx

Find the RankedWatchlistPlaceholder usage and replace it with
<PreMarketWatchlistPanel />.

The existing placeholder had "Ranked Watchlist" as title with Sprint 23 label.
The new panel IS the Sprint 21.7 deliverable — no "Coming" badge needed.

### 3. Add useWatchlist import

PreMarketLayout.tsx needs to import useWatchlist. Check if it's already
imported anywhere in the file — add if needed.

### 4. Write Vitest tests for the new component

In argus/ui/src/features/dashboard/PreMarketLayout.test.tsx (already exists):
- test: renders PreMarketWatchlistPanel with mock watchlist data
- test: shows FMP badge when scan_source is "fmp"
- test: shows Static badge when scan_source is "static"
- test: renders loading skeleton when isLoading=true
- test: renders empty state when watchlist has 0 symbols

## Constraints
- Do NOT modify WatchlistSidebar.tsx or WatchlistItem.tsx
- Do NOT create new API hooks — reuse useWatchlist()
- Do NOT add Catalyst or Quality columns — those are Sprint 23/24
- Panel must render the same DOM structure in all states (no conditional
  skeleton/content swaps that change the element tree — key lesson from
  React conditional rendering pitfall in project memory)
- Use existing Card, CardHeader, Badge, Skeleton components — no new component files

## Test Targets
- npx vitest run argus/ui/src/features/dashboard/
- npx vitest run (full suite)
- Minimum new Vitest tests: 5

## Definition of Done
- [ ] RankedWatchlistPlaceholder replaced with PreMarketWatchlistPanel
- [ ] Panel renders with symbol list, gap%, source badge, selection reason
- [ ] FMP/Static source badge correct
- [ ] Loading skeleton renders (same DOM structure as content)
- [ ] Empty state renders
- [ ] 5 new Vitest tests pass
- [ ] Full Vitest suite passes (291 + new)

## Regression Checklist
| Check | Verify |
|-------|--------|
| WatchlistSidebar unchanged | git diff WatchlistSidebar.tsx = no changes |
| PreMarketLayout other cards intact | screenshot: SessionSummaryCard, GoalTracker visible |
| DashboardPage renders correctly | no console errors in dev mode |

## Close-Out
Follow .claude/skills/close-out.md. Include a screenshot description of the
Pre-Market Watchlist panel in the close-out notes.
