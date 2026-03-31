---BEGIN-REVIEW---

# Sprint 28.75 Session 2 — Tier 2 Review Report

**Reviewer:** Tier 2 Automated Review (Claude Opus 4.6)
**Date:** 2026-03-30
**Commit reviewed:** 01e6a05 (`feat(ui): Sprint 28.75 S2 — frontend bug fixes + UI improvements`)
**Branch:** sprint-28.75

## Summary

Session 2 addressed six frontend bug fixes and UI improvements found in the
March 30 market session debrief. All six requirements were implemented: VixRegimeCard
viewport fix, TodayStats win rate display, closed positions limit increase, server-side
trade stats endpoint, Avg R metric card, and colored current price in open positions.

## Test Results

| Suite | Count | Status |
|-------|-------|--------|
| pytest | 3,966 | All passing |
| Vitest | 687 passing, 1 failed | Pre-existing GoalTracker.test.tsx failure (unrelated) |
| New tests | 3 pytest + 8 Vitest = 11 | All passing |

## Protected File Verification

All files that should NOT have been modified are confirmed unchanged:
- `argus/execution/order_manager.py` -- no diff
- `argus/strategies/` -- no diff
- `argus/core/events.py` -- no diff
- `argus/backtest/` -- no diff

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| Changes to bracket order creation | No |
| Changes to risk manager | No |
| Changes to event bus | No |
| Changes to strategy base class | No |
| Changes to config loading architecture | No |
| Changes to reconciliation logic | No |
| New WebSocket endpoints | No |

No escalation criteria triggered.

## Review Focus Items

### F1: VixRegimeCard no longer has h-full or equivalent stretch styling
**PASS.** The `h-full` class was already removed from VixRegimeCard.tsx (grep confirms
no `h-full` in the file). The session wrapped VixRegimeCard in `<motion.div variants={staggerItem}>`
on all three DashboardPage layouts (phone, desktop, tablet) for consistent stagger animation.
New test verifies no `h-full` class on the rendered card.

### F2: TodayStats win rate fix addresses root cause
**PASS.** The close-out documents the investigation: all Trade model instances require
`exit_price` as a `float` field, so `compute_metrics` never filters them out. The root
cause was purely frontend: `winRate > 0` showed a dash for a legitimate 0% win rate
when trades existed. Changed to `trades > 0` which correctly distinguishes "no trades"
from "no wins." This is the correct fix.

### F3: Stats endpoint is JWT-protected
**PASS.** `_auth: dict = Depends(require_auth)` is present. Backend test
`test_stats_unauthenticated` confirms 401 on unauthenticated access.

### F4: Stats endpoint query uses same filter logic as trades endpoint
**PASS.** The `/stats` endpoint accepts the same four filter parameters
(`strategy_id`, `date_from`, `date_to`, `outcome`) and calls the same
`query_trades()` and `count_trades()` methods. Filter logic is consistent.

### F5: OpenPositions closed tab limit increase
**PASS with note.** Limit changed from 50 to 250. The spec suggested 500 but the
trades API enforces `le=250`. The close-out correctly documents this deviation. Badge
count uses `total_count` from the API for accuracy beyond the page limit.

### F6: P&L column / current price coloring
**PASS.** Current price is colored `text-argus-profit` when above entry,
`text-argus-loss` when below. The existing PnlValue component handles dollar P&L
display. Coloring logic applied to both the desktop and compact table layouts.
For long-only positions, `livePrice > entry_price` correctly indicates profit.

### F7: refetchOnWindowFocus change
**PASS.** Changed from `false` to `true` on `useTrades`. The new `useTradeStats`
hook also uses `refetchOnWindowFocus: true`. Both have `staleTime: 30_000` and
`refetchInterval: 30_000`, so window focus refetch will only trigger if data is
stale (>30s old), not on every tab switch. This is reasonable.

## Findings

### F1 (LOW): Missing OpenPositions test for closed tab limit
The spec called for a Vitest test: "OpenPositions: closed tab respects higher limit."
No such test was added. The minimum test count in the spec was "4 Vitest + 2 pytest";
the session delivered 8 Vitest + 3 pytest, exceeding the total but missing this
specific test. The limit change is trivially correct (50 to 250 in a single location),
so the risk is negligible.

### F2 (LOW): Stats endpoint total_trades/metrics potential mismatch at >10,000 trades
The `/stats` endpoint queries `trades_data` with `limit=10000` but gets `total_count`
from `count_trades()` (unbounded). If a filtered result exceeds 10,000 trades,
`total_trades` would be correct but `wins`, `losses`, `win_rate`, and `net_pnl` would
be computed from a truncated subset. For an intraday trading system this is extremely
unlikely (would require 10,000+ trades matching a single filter), but the hardcoded
limit creates a theoretical inconsistency. A constant or comment would make the intent
clearer.

### F3 (LOW): Stats endpoint duplicates computation logic (expected, per escalation criteria)
The stats endpoint reuses `compute_metrics()` from `argus/analytics/performance.py`,
which is the same function used by the dashboard summary endpoint. This is reuse, not
duplication -- the escalation criterion was about duplicating *significant logic*, and
this is a single function call. No concern.

### F4 (INFO): R3 limit deviation documented
The spec said 500, implementation used 250 due to API constraint (`le=250`). Close-out
documents this. The badge count uses `total_count` from the API, so display is accurate
regardless of the fetch limit.

### F5 (INFO): Self-assessment MINOR_DEVIATIONS is accurate
The close-out correctly self-assessed as MINOR_DEVIATIONS due to the R3 limit
difference (250 vs 500) and the R6 partial pre-existence (P&L column already existed;
only current price coloring was added). Both deviations are well-documented.

## Route Ordering Verification

The `/stats` route is registered at line 79, before the catch-all `""` route at
line 136 and the parameterized `/{trade_id}` routes. FastAPI route ordering is correct;
`/stats` will not be shadowed.

## Scope Adherence

All changes are within scope. No files outside the UI, API routes, and test directories
were modified. No trading engine behavior was changed. The session addressed exactly the
six requirements specified.

## Verdict

**CONCERNS**

Two low-severity findings documented: (1) missing OpenPositions Vitest test that was
specifically called for in the spec, and (2) theoretical stats endpoint mismatch at
>10K trades. Neither is blocking -- the implementation is correct and complete for all
practical purposes.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "28.75",
  "session": "S2",
  "reviewer": "tier-2-automated",
  "verdict": "CONCERNS",
  "confidence": 0.92,
  "findings": [
    {
      "id": "F1",
      "severity": "LOW",
      "category": "test-coverage",
      "description": "Missing OpenPositions Vitest test for closed tab limit increase (spec called for it explicitly)",
      "location": "argus/ui/src/features/dashboard/OpenPositions.test.tsx (not modified)",
      "recommendation": "Add a test verifying useTrades is called with limit=250 for the closed tab"
    },
    {
      "id": "F2",
      "severity": "LOW",
      "category": "correctness",
      "description": "Stats endpoint queries trades with limit=10000 but total_count is unbounded; metrics could mismatch at >10K trades",
      "location": "argus/api/routes/trades.py:112",
      "recommendation": "Add a comment explaining the 10K cap or use total_count to validate consistency"
    }
  ],
  "escalation_triggers": [],
  "tests_pass": true,
  "test_counts": {
    "pytest": 3966,
    "vitest_pass": 687,
    "vitest_fail": 1,
    "vitest_fail_preexisting": true,
    "new_tests": 11
  },
  "protected_files_clean": true,
  "scope_adherence": "all 6 requirements implemented, no out-of-scope changes"
}
```
