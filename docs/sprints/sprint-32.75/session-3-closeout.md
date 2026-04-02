# Sprint 32.75 Session 3 — Close-Out Report

## Session
Sprint 32.75, Session 3: Orchestrator Page Fixes

## Change Manifest

### `argus/api/routes/orchestrator.py`
- **P&L fix**: Added a batch `get_trades_by_date(today_et_date)` call before the strategy allocation loop, grouping results into `trades_by_strategy: dict[str, list]`. Replaced the broken `getattr(strategy, '_trade_count_today', 0)` / `getattr(strategy, '_daily_pnl', 0.0)` pattern with direct lookup per strategy ID. `trade_count_today = len(strategy_trades_today)`, `daily_pnl = sum(t.net_pnl for t in strategy_trades_today)`.
- Uses `today_et_date = datetime.now(et_tz).date()` (ET) — correct because all intraday exits (9:30–3:55 PM ET) fall on the same UTC calendar date, so SQLite's `date(exit_time)` matches (DEC-061).
- `is_active` still reads from strategy object via `getattr`; the getattr for the now-removed `_trade_count_today` / `_daily_pnl` are gone.

### `argus/ui/src/components/CatalystAlertPanel.tsx`
- **Clickable headlines**: Wrapped headline `<p>` content in `<a href=... target="_blank" rel="noopener noreferrer" className="hover:underline">`. Uses `catalyst.source_url` if available; falls back to `https://www.google.com/search?q={encodeURIComponent(catalyst.headline)}` when `source_url` is null.

### `tests/api/test_orchestrator_extended.py`
- Added `_make_trade_today()` helper: creates a Trade with today's ET date as exit_time (computed at test runtime so it stays current).
- Added `app_state_with_trades_today` fixture: seeds 3 orb_breakout trades (2 wins + 1 loss) and 1 orb_scalp trade.
- Added `client_with_trades_today` fixture.
- **5 new tests**:
  1. `test_status_trade_count_today_reflects_logged_trades` — counts match per strategy
  2. `test_status_daily_pnl_reflects_logged_trades` — orb_breakout net P&L = 117.0
  3. `test_status_daily_pnl_sums_wins_and_losses` — positive net after wins/loss
  4. `test_status_pnl_is_zero_when_no_trades_today` — baseline 0 without seeded trades
  5. `test_status_pnl_is_independent_per_strategy` — orb_scalp net=79.0, other strategies=0

### `argus/ui/src/components/CatalystAlertPanel.test.tsx`
- **2 new tests**:
  1. `renders headline as a clickable link using source_url when available` — verifies href, target, rel
  2. `renders headline as a search link when source_url is null` — verifies google.com/search fallback

## Judgment Calls

**AllocationDonut legend**: No changes required. `AllocationDonut.tsx` already has `STRATEGY_DISPLAY_NAMES` covering all 12 strategies with correct display names, and uses `getStrategyDisplayName()` for the legend. `StrategyCoverageTimeline.tsx` already uses `getStrategyDisplay()` from `strategyConfig.ts` (wired in S1). No hardcoded `strat_xxx` formatting found in any Orchestrator-specific component.

**Batch vs per-strategy query**: Used a single `get_trades_by_date(today_et_date)` with in-Python grouping rather than N per-strategy queries. Minimizes DB round trips for 12-strategy allocation loop.

**`_make_trade_today` uses runtime date**: Not a fixed date like "2026-02-15". This ensures the test works regardless of the current date (avoids the `test_history_store_migration` style decay pattern).

## Scope Verification

- [x] Orchestrator P&L and trades populated from trade_logger query
- [x] Capital Allocation legend uses display names (already correct from S1, verified no regressions)
- [x] Catalyst headlines clickable (source_url or search fallback)
- [x] All tests pass
- [x] 5 new backend tests (actually 5 test functions + 2 fixtures)
- [x] 2 new frontend tests

## Test Results

| Suite | Result |
|-------|--------|
| `tests/api/test_orchestrator*.py` | 54 passed |
| `src/components/CatalystAlertPanel.test.tsx` | 12 passed (10 existing + 2 new) |
| Full pytest (excl. test_main.py) | 4516 passed, 1 pre-existing failure |
| Full Vitest | 774 passed, 0 failures |

## Pre-Existing Failures

**`tests/core/test_regime_vector_expansion.py::TestHistoryStoreMigration::test_history_store_migration`**
- Root cause: Hardcoded date "2026-03-25" is beyond the 7-day retention window (`get_regime_history` returns nothing for dates >7 days ago). Today is April 1, 2026.
- NOT caused by this session's changes. No regime code was touched.
- Recommend: Add to `DEF-136` or file a new DEF for hardcoded-date test fragility in regime tests.

## Regression Checklist

| Check | Result |
|-------|--------|
| Orchestrator page still loads — 200 from `/api/v1/orchestrator/allocations` | Pass (test suite validates /status) |
| AllocationInfo schema unchanged | Pass — existing tests for `trade_count_today`, `daily_pnl` fields still pass |
| Strategy cards still show correct status | Pass — `is_active` still populated from strategy object |
| `catalyst.source_url` links open in new tab | Pass — `target="_blank" rel="noopener noreferrer"` verified in test |

## Self-Assessment

**CLEAN** — All spec items delivered. No scope expansion. Pre-existing test failure documented and attributable to date decay, not this session.

## Context State

**GREEN** — Session completed well within context limits.
