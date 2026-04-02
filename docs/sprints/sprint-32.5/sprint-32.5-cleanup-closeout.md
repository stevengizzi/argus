# Sprint 32.75 Cleanup — Close-Out

**Sprint:** 32.75 (Post-32.5 Cleanup Sweep)
**Date:** 2026-04-01
**Branch:** sprint-32.75-cleanup
**Sessions:** 1

---

## Fixes Applied

### Fix 1 — GoalTracker.test.tsx: 3 Pre-Existing Failures (DEF-136)

**File:** `argus/ui/src/features/dashboard/GoalTracker.test.tsx`

Root cause: `calculateTradingDays()` calls `new Date()` at render time. On April 1
(day 1 of month, 1 trading day elapsed), `avgDaily = currentPnl / 1`, causing:
- Tests 1 & 2: `avgDaily` matched the current P&L value → `getByText` found two
  elements (the P&L display div and the Avg daily span), throwing "Found multiple
  elements".
- Test 3: `paceRatio = 500 / (5000 × 0.045) ≈ 2.2` → "Ahead of pace" instead of
  "Behind pace".

Fix: Added `vi.useFakeTimers()` + `vi.setSystemTime(new Date('2026-04-15T10:00:00Z'))`
in `beforeEach` (with `vi.useRealTimers()` cleanup in `afterEach`). April 15 = 9
trading days elapsed, 11 remaining.

- 9 elapsed days → `avgDaily = $500/9 = $55.56` (≠ $500, no ambiguity)
- `elapsedPct = 45%` → `expectedPnl = $2,250` → paceRatio = 0.22 → "Behind pace" ✓

### Fix 2 — ExperimentsPage.tsx: bestSharpe/bestWr loop recomputation

**File:** `argus/ui/src/pages/ExperimentsPage.tsx` (line ~224)

Lifted `bestSharpe` and `bestWr` out of the `.map()` callback and into an IIFE
wrapping the `variants.map(...)` call. These values were previously recomputed
O(n) times (once per row) instead of once per render.

### Fix 3 — ExperimentsPage.tsx: Mode column sort key

**File:** `argus/ui/src/pages/ExperimentsPage.tsx` (line ~169)

Changed `sortKey="trade_count"` → `sortKey="mode"` on the Mode column `SortHeader`.
Added `'mode'` to the `SortKey` union type. Updated the sort comparator to use
`localeCompare` for the string `mode` field instead of numeric subtraction.

### Fix 4 — architecture.md: keyboard shortcut range

**File:** `docs/architecture.md` (line 1768)

Updated `1`–`7` → `1`–`9` to reflect Observatory (shortcut `8`, Sprint 25) and
Experiments (shortcut `9`, Sprint 32.5).

### Fix 5 — Vitest count correction (713 → 711)

**Files updated:**
- `docs/project-knowledge.md` (lines 14, 86): 713 → 711
- `docs/sprint-history.md` (lines 2292, 2325): 713 → 711, +13 → +11, ~5,202 → ~5,200
- `docs/roadmap.md` (line 121): 713 → 711
- `CLAUDE.md` (line 33): 713 → 711, updated pre-existing failure note

---

## Test Results

| Suite | Before | After |
|-------|--------|-------|
| Vitest | 708 passing, 3 failing (GoalTracker) | **711 passing, 0 failing** |
| pytest | 4,489 passing | 4,489 passing (unchanged — no backend changes) |

---

## DEF Status

- **DEF-136** (GoalTracker.test.tsx — 3 pre-existing Vitest failures): **RESOLVED**

---

## Scope Verification

- No backend `.py` files modified ✓
- No new features or refactoring beyond the 5 specified fixes ✓
- All changes minimal and targeted ✓

## Self-Assessment: CLEAN
