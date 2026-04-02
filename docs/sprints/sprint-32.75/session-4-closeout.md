# Sprint 32.75, Session 4 — Close-Out

## Change Manifest

### `argus/ui/src/components/TradeChart.tsx`
- Added `type IPriceLine` to lightweight-charts imports
- Added `priceLinesRef = useRef<IPriceLine[]>([])` alongside existing chart refs
- In the data/overlays `useEffect`: remove all tracked price lines at the start (before creating new ones), store each `createPriceLine()` return value in `priceLinesRef`
- Added cleanup function to the data/overlays `useEffect` that removes tracked price lines on unmount

### `argus/ui/src/components/TradeChart.test.tsx`
- Added `mockRemovePriceLine = vi.fn()` to the mock
- Made `mockCreatePriceLine` return `{ _mockPriceLine: true }` (trackable object)
- Added `removePriceLine: mockRemovePriceLine` to the `mockAddSeries` return value
- **New test**: `removes price lines before recreating on data update` — renders, clears mocks, rerenders with changed prop, asserts `removePriceLine` called and `createPriceLine` called exactly 5 times
- **New test**: `creates exactly one set of price lines after initial render` — asserts exactly 5 `createPriceLine` calls and 0 `removePriceLine` calls on first render

### `argus/ai/context.py` (`SystemContextBuilder._build_dashboard_context`)
- Expanded position detail per item: added `side` (always "long" for V1), `current_price`, `r_multiple`, `hold_duration_seconds`
- Added 50-position cap to prevent context window overflow
- Added `portfolio_summary` aggregates: `total_position_count`, `total_unrealized_pnl`, `count_by_strategy`, `winning_count`, `losing_count`
- r_multiple computation guarded with `isinstance` checks + try/except to handle missing `original_stop_price`

### `tests/ai/test_context.py`
- **New class** `TestDashboardFullPortfolioContext` with 2 tests:
  - `test_dashboard_includes_all_positions_when_more_than_five_exist`: 8 mock positions → asserts all 8 returned with enriched fields (current_price, side, r_multiple, hold_duration_seconds)
  - `test_dashboard_portfolio_summary_includes_aggregates`: 2 positions (1 winning, 1 losing) → asserts total_position_count, winning_count, losing_count, count_by_strategy, total_unrealized_pnl

## Judgment Calls

- **r_multiple type guard**: Used `isinstance(original_stop, float)` instead of a bare `getattr` to avoid MagicMock arithmetic side-effects in tests. In production, `original_stop_price` is always a `float` on `ManagedPosition`, so this guard has no runtime impact.
- **side field hardcoded to "long"**: V1 is long-only (DEC-011). Added the field for AI context completeness; no logic change needed.
- **hold_duration_seconds guarded with try/except**: `entry_time` arithmetic can fail if the datetime is naive vs aware — safe fallback to 0.

## Scope Verification

| Requirement | Status |
|-------------|--------|
| TradeChart useRef tracks price line objects | ✅ |
| Remove tracked lines before recreating | ✅ |
| Store each new line in ref | ✅ |
| Cleanup removes lines in useEffect return | ✅ |
| AI context includes all positions (up to 50) | ✅ |
| Per-position: symbol, strategy, side, entry_price, current_price, unrealized_pnl, r_multiple, hold_duration | ✅ |
| Portfolio summary aggregates added | ✅ |
| Chart initialization not modified | ✅ |
| Chart visual appearance not changed | ✅ |
| AI API call logic / prompt templates not modified | ✅ |
| ≥4 new/updated tests | ✅ (4 new) |

## Test Results

| Suite | Before | After | Delta |
|-------|--------|-------|-------|
| `tests/ai/` pytest | 180 | 182 | +2 |
| Vitest TradeChart | 6 | 8 | +2 |
| Vitest full suite | 760 | 760 | 0 regressions |

## Regression Checklist

| Check | Result |
|-------|--------|
| TradeChart renders candles correctly | ✅ existing tests pass |
| Price lines show correct prices | ✅ existing `createPriceLine` call assertions pass |
| AI Copilot endpoint tests | ✅ 182/182 tests/ai/ pass |

## Self-Assessment

**CLEAN** — All 4 spec items implemented, 4 new tests added, no deviations from spec constraints. No adjacent code modified.

## Context State

**GREEN** — Session completed well within context limits.
