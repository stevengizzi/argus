---BEGIN-REVIEW---

# Tier 2 Review -- Sprint 32.75 Session 3

**Reviewer:** Automated Tier 2
**Session:** Sprint 32.75, Session 3 -- Orchestrator Page Fixes
**Date:** 2026-04-01

## Test Results

| Suite | Result |
|-------|--------|
| `tests/api/test_orchestrator_extended.py` | 31 passed |
| `tests/api/test_orchestrator*.py` (all) | 54 passed |
| `src/components/CatalystAlertPanel.test.tsx` | 12 passed (10 existing + 2 new) |
| `src/features/orchestrator/` (all) | 65 passed across 10 test files |
| Pre-existing failure | `test_history_store_migration` -- hardcoded date decay, unrelated |

All session-relevant tests pass. Zero regressions.

## Diff Analysis

### `argus/api/routes/orchestrator.py` (+10 lines, -4 lines)
- Added a batch `get_trades_by_date(today_et_date)` call before the allocation loop (line 249).
- Grouped results into `trades_by_strategy: dict[str, list]` using `setdefault`.
- Replaced broken `getattr(strategy, '_trade_count_today', 0)` / `getattr(strategy, '_daily_pnl', 0.0)` with direct lookups from the grouped dict.
- `daily_pnl = sum(t.net_pnl for t in strategy_trades_today)` correctly uses `Trade.net_pnl` (gross minus commission, computed in `__post_init__`).
- `is_active` still uses `getattr(strategy, "is_active", True)` -- correct, this field lives on the strategy object.

### `argus/ui/src/components/CatalystAlertPanel.tsx` (+7 lines, -1 line)
- Headline text wrapped in `<a>` tag with `target="_blank"`, `rel="noopener noreferrer"`, `className="hover:underline"`.
- `href` uses `catalyst.source_url` with nullish coalescing to Google search fallback using `encodeURIComponent`.
- Clean, minimal change.

### `tests/api/test_orchestrator_extended.py` (+177 lines)
- `_make_trade_today()` helper creates trades with today's ET date (runtime-computed, avoids date decay).
- `app_state_with_trades_today` fixture seeds 4 trades across 2 strategies.
- 5 new test functions covering: trade count accuracy, P&L sum, win/loss netting, zero-trade baseline, per-strategy isolation.
- All assertions use concrete expected values (e.g., 117.0 for 3 trades with known gross/commission).

### `argus/ui/src/components/CatalystAlertPanel.test.tsx` (+39 lines)
- 2 new tests: one for `source_url` present (verifies href, target, rel attributes), one for `source_url: null` (verifies Google search fallback URL).

## Spec Compliance

| Requirement | Status |
|-------------|--------|
| 1. P&L bug fix -- replace getattr with trade_logger query | PASS |
| 2. Capital Allocation legend -- verify display names | PASS (verified correct from S1, no changes needed) |
| 3. Catalyst headlines clickable with security attributes | PASS |
| 5+ new backend tests | PASS (5 tests) |
| 1+ new frontend tests | PASS (2 tests) |

## Session-Specific Checks

1. **ET date correctness:** PASS. `today_et_date = datetime.now(et_tz).date()` where `et_tz = ZoneInfo("America/New_York")`. The `get_trades_by_date()` query uses `date(exit_time) = ?` in SQLite. For all intraday exits (by 3:55 PM ET = 7:55 PM UTC), the UTC calendar date matches the ET calendar date. The comment in the code correctly explains this invariant and references DEC-061.

2. **Zero-trade safety:** PASS. `trades_by_strategy.get(strategy_id, [])` returns an empty list for strategies with no trades. `len([]) == 0` and `sum(... for t in []) == 0.0`. Test `test_status_pnl_is_zero_when_no_trades_today` explicitly validates this path.

3. **rel="noopener noreferrer" present:** PASS. Verified in source (`CatalystAlertPanel.tsx` line 101) and in test assertions (`expect(link).toHaveAttribute('rel', 'noopener noreferrer')`).

## Constraint Verification

| Constraint | Status |
|------------|--------|
| OrderManager not modified | PASS -- zero diff lines in `argus/execution/` |
| BaseStrategy not modified | PASS -- zero diff lines in `argus/strategies/base_strategy.py` |
| Risk Manager not modified | PASS -- zero diff lines in `argus/core/risk_manager.py` |
| AllocationInfo schema unchanged | PASS -- fields `trade_count_today` and `daily_pnl` already existed on the model; only the population logic changed |

## Escalation Criteria Check

Criterion #5 (trade-to-strategy attribution gap): NOT TRIGGERED. The `get_trades_by_date()` query returns `Trade` objects with correctly populated `strategy_id` fields. Tests confirm per-strategy isolation works. No data integrity issues observed.

## Findings

**F1 (NOTE):** `trades_by_strategy: dict[str, list]` on line 250 of `orchestrator.py` uses bare `list` instead of `list[Trade]`. Per project code style rules (parameterized generics required), this should be `dict[str, list[Trade]]`. However, `Trade` is not imported in this file and adding the import solely for this annotation would be a scope expansion. The `from __future__ import annotations` import means this is a string annotation anyway and has no runtime impact. Cosmetic only.

**F2 (NOTE):** The close-out report claims "4516 passed, 1 pre-existing failure" for the full pytest suite. The pre-existing failure (`test_history_store_migration`) is confirmed as a hardcoded-date decay issue (date "2026-03-25" is >7 days ago from today April 1, 2026). This should be tracked as a new DEF item or added to an existing one. The close-out suggests adding to DEF-136 but DEF-136 was for GoalTracker.test.tsx and is already resolved. A new DEF item would be more appropriate.

## Verdict

**CLEAR**

All three spec requirements delivered correctly. The P&L bug fix is sound -- it replaces unreliable `getattr` on private attributes that were never populated with a direct database query using proper ET date handling. The catalyst link change is minimal and secure. Test coverage is adequate with 5 backend tests covering the core paths (trade count, P&L sum, netting, zero baseline, per-strategy isolation) and 2 frontend tests covering both link scenarios. No forbidden files were modified. No escalation criteria triggered.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "sprint": "32.75",
  "session": 3,
  "findings_count": 2,
  "findings": [
    {
      "id": "F1",
      "severity": "NOTE",
      "description": "Bare `list` type annotation on `trades_by_strategy` dict instead of parameterized `list[Trade]`. Cosmetic, no runtime impact.",
      "file": "argus/api/routes/orchestrator.py",
      "line": 250
    },
    {
      "id": "F2",
      "severity": "NOTE",
      "description": "Pre-existing test failure (test_history_store_migration) due to hardcoded date decay needs a new DEF item, not DEF-136 as the close-out suggests.",
      "file": "tests/core/test_regime_vector_expansion.py",
      "line": 304
    }
  ],
  "tests_passed": true,
  "spec_compliance": "FULL",
  "escalation_triggered": false,
  "constraints_respected": true
}
```
