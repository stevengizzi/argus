---BEGIN-REVIEW---

# Sprint 32.8, Session 6h — Tier 2 Review

**Reviewer:** Automated Tier 2  
**Date:** 2026-04-02  
**Verdict:** CLEAR

## Summary

Session 6h made three targeted fixes across three UI files to resolve visual and behavioral
discrepancies between the Live Trades and Shadow Trades tabs. All changes are correct, well-scoped,
and test-verified. No escalation criteria triggered.

## Files Changed

| File | Change Type | Lines |
|------|------------|-------|
| `argus/ui/src/features/trades/ShadowTradesTab.tsx` | Bug fix + refactor | +41 / -23 |
| `argus/ui/src/features/trades/TradeTable.tsx` | Styling fix | +3 / -3 |
| `argus/ui/src/pages/TradesPage.tsx` | Styling fix | +1 / -1 |

## Review Criteria Analysis

### 1. isPlaceholderData guard — does it fix the root cause?

**Verdict: Correct.** The root cause is well-identified: `keepPreviousData` in TanStack Query
returns stale `data` from the prior query key while the new query is in-flight. The `useEffect`
was firing with this stale data, repopulating `allTrades` with old positions. The guard
`if (!data || isPlaceholderData) return;` correctly prevents the effect from running on placeholder
data. `isPlaceholderData` is included in the dependency array, which is correct — when the fresh
data arrives, `isPlaceholderData` flips to `false`, triggering the effect with fresh data.

The `useShadowTrades` hook returns TanStack's standard `useQuery` result which includes
`isPlaceholderData` (verified in the hook source at line 23-31).

### 2. useMemo stats computation — correctness and null-safety

**Verdict: Correct.** The `useMemo` at lines 640-656 correctly:
- Filters for non-null `theoretical_pnl` before computing win rate and avg P&L
- Filters for non-null `theoretical_r_multiple` before computing avg R
- Returns `null` for each stat when the filtered array is empty
- Uses non-null assertions (`!`) only after the `!== null` filter, which is safe
- Depends on `[allTrades]`, which is the correct dependency

### 3. SummaryStats refactor — both call sites

**Verdict: Correct.** Both call sites updated:
- Empty state (line 683): passes `winRate={null} avgPnl={null} avgR={null} totalCount={0}`
- Data state (lines 691-696): passes pre-computed `summaryStats.*` values and `totalCount`
- The `SummaryStats` component now renders purely from props — no internal computation

### 4. space-y-4 on live wrapper — spacing and animation

**Verdict: Correct.** Line 290: `className={activeTab === 'live' ? 'space-y-4' : 'hidden'}`
matches the Shadow Trades tab's root `<div className="space-y-4">` (ShadowTradesTab line 659).
The `space-y-4` applies `margin-top` to child elements, which does not conflict with Framer
Motion's `variants={staggerItem}` on the inner `motion.div` elements (stagger animations control
opacity and transform, not spacing).

### 5. thead/tbody styling changes — sticky header safety

**Verdict: Correct.** Moving `bg-argus-surface-2` from `<tr>` to `<thead>` (which already has
`sticky top-0 z-10`) is safer for sticky headers. The background color on `<thead>` ensures
content scrolling beneath the header is occluded. Adding `bg-argus-surface` to `<tbody>` provides
an explicit background rather than inheriting from the outer container.

### 6. Test IDs preserved

**Verdict: All preserved.** Verified the following test IDs remain in the changed files:
- `shadow-trades-tab`, `shadow-summary-stats`, `shadow-trade-table`, `shadow-trade-row`
- `shadow-loading-state`, `shadow-error-state`, `shadow-empty-state`
- `shadow-scroll-sentinel`, `shadow-loading-more`
- `shadow-quick-filter-*`, `shadow-date-from`, `shadow-date-to`
- `sort-*` columns, `reason-cell`
- `trade-table-scroll`, `sort-entry_time`, `sort-symbol`, `sort-strategy`, etc.

### 7. TypeScript issues

**Verdict: None introduced.** No new types, no `any` usage, no type assertions beyond the
pre-existing `as SortKey` cast in the sort handler. The `SummaryStatsProps` interface change
is clean — all four props are properly typed.

## Regression Checklist

| # | Check | Result |
|---|-------|--------|
| 5 | Live Trades tab retains all existing functionality | PASS — sort, filter, stats bar, table all present |
| 6 | Shadow Trades tab shows all shadow trade data | PASS — filters, stats, table, infinite scroll |
| 8 | Vitest baseline passes | PASS — 846/846 (115 files, 0 failures) |
| 9 | No Python files modified | PASS — only 3 UI files changed |
| 10 | No event definitions changed | PASS |
| 11 | No database schema changes | PASS |
| 12 | No config file changes | PASS |

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| Trading engine modification | No |
| Event definition change | No |
| API contract change | No |
| Performance regression | No |
| Data loss | No |
| Test baseline regression | No — 846/846 pass |

## Test Results

- **Scoped tests (trades + TradesPage):** 49/49 passed
- **Full Vitest suite:** 846/846 passed (115 files)
- **Pytest:** Not run (no backend changes — appropriate)

## Findings

No issues found. The implementation is clean, correctly scoped, and well-documented.

## Close-Out Report Assessment

The close-out report is accurate. Self-assessment of CLEAN is justified. The judgment call about
not adding `opacity-80` to Live Trades tbody is reasonable — the P&L row coloring is a Live-only
visual feature that would be dimmed by uniform opacity.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "sprint": "32.8",
  "session": "6h",
  "reviewer": "tier-2-automated",
  "date": "2026-04-02",
  "files_reviewed": [
    "argus/ui/src/features/trades/ShadowTradesTab.tsx",
    "argus/ui/src/features/trades/TradeTable.tsx",
    "argus/ui/src/pages/TradesPage.tsx",
    "argus/ui/src/features/trades/TradeStatsBar.tsx",
    "argus/ui/src/hooks/useShadowTrades.ts"
  ],
  "tests_passed": true,
  "test_counts": {
    "vitest_total": 846,
    "vitest_passed": 846,
    "vitest_failed": 0,
    "scoped_total": 49,
    "scoped_passed": 49
  },
  "findings": [],
  "escalation_triggered": false
}
```
