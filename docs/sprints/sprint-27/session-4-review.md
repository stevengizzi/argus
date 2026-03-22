---BEGIN-REVIEW---
# Sprint 27 Session 4 — Tier 2 Review

**Reviewer:** Automated Tier 2
**Session:** Sprint 27, Session 4 (Bar Loop + Fill Model)
**Date:** 2026-03-22
**Verdict:** CLEAR

---

## 1. Spec Compliance

All 7 items from the Definition of Done are satisfied:

| Requirement | Status | Notes |
|-------------|--------|-------|
| `_run_trading_day()` bar-by-bar without tick synthesis | PASS | No tick synthesis imports or calls anywhere in engine.py |
| `_check_bracket_orders()` bar-level fill model, correct priority | PASS | Stop > Target > Time Stop > EOD. See fill model analysis below. |
| `_on_candle_event()` routes signals through risk manager | PASS | Lines 207-219; unchanged from S3 |
| `_get_daily_bars()` chronologically sorted multi-symbol bars | PASS | concat + sort_values("timestamp"), lines 296-298 |
| Data loading from HistoricalDataFeed integrated | PASS | `_load_data()` lines 223-259 |
| All existing tests pass | PASS | 29/29 (14 S3 + 15 S4) |
| 15 new tests written and passing | PASS | Tests 1-15 all present and passing |

## 2. Critical Review: Fill Model Priority

Examined every code path in `_check_bracket_orders()` (lines 399-467):

**Path 1 — Stop triggers (line 442):** `bar_low <= stop_price` checked first. If true, `simulate_price_update` at stop price, then `return` (line 447). Targets and time stop are never evaluated. CORRECT.

**Path 2 — Both stop and target could trigger:** The stop check comes first and returns early. Target check is never reached. Stop wins. CORRECT per worst-case-for-longs.

**Path 3 — Target only (lines 449-462):** Only reached if stop did NOT trigger. Target orders sorted ascending (T1 before T2). Freshness check (`still_pending`) prevents double-processing if T1 fill caused position close. CORRECT.

**Path 4 — Time stop (lines 464-467):** Only reached after stop and target checks. Delegates to `_check_time_stop()` which:
- Checks `is_fully_closed` to skip already-closed positions (line 494)
- Checks elapsed time against `time_stop_seconds` (line 500)
- If bar also hits stop price, uses stop price (worst case) (lines 507-509)
- Otherwise uses close price (line 511)
CORRECT per backtesting.md exit priority rules.

**Path 5 — No trigger:** If bar is between stop and target and no time stop, nothing happens. Brackets remain pending. CORRECT.

No escalation criteria triggered. The fill model is correct.

## 3. Constraint Verification

| Constraint | Status | Evidence |
|------------|--------|----------|
| No tick synthesis | PASS | `grep "tick_synthesizer\|synthesize_ticks" engine.py` returns empty |
| No asyncio.sleep(0) | PASS | `grep "asyncio.sleep" engine.py` returns empty |
| No asyncio.create_task | PASS | `grep "create_task" engine.py` returns empty |
| Time stop checks for stop hit | PASS | Lines 504-509: explicit stop bracket check with worst-case price |
| `_get_daily_bars()` interleaves by timestamp | PASS | Line 297: `sort_values("timestamp")` after `pd.concat` |
| Strategy receives CandleEvents only for watchlist | PASS | `_get_daily_bars(trading_day, watchlist)` filters to watchlist symbols only |

## 4. Regression Checklist

| # | Check | Result |
|---|-------|--------|
| R2 | Replay Harness unchanged | PASS — `git diff HEAD~1 argus/backtest/replay_harness.py` empty |
| R3 | BacktestDataService unchanged | PASS — `git diff HEAD~1 argus/backtest/backtest_data_service.py` empty |
| R4 | All VectorBT files unchanged | PASS — `git diff HEAD~1 argus/backtest/vectorbt_*.py` empty |
| R5 | All strategy files unchanged | PASS — `git diff HEAD~1 argus/strategies/` empty |

## 5. Test Results

- Session tests: 29/29 passed (0.36s)
- Full suite: 2,982 passed, 0 failures (49s with xdist)
- Test count: 2,982 (2,925 baseline + 57 new from Sprint 27 S1-S4)

## 6. Escalation Criteria Check

| # | Criterion | Triggered? |
|---|-----------|------------|
| 2 | Fill model produces incorrect results | NO — All 6 fill model tests pass with correct prices |
| 3 | Strategy behavior differs between engine and direct test | NO — Same strategy instances, same event flow |
| 6 | Engine slower than Replay Harness | N/A — No performance comparison in this session |
| 9 | Any existing backtest test fails | NO — 2,982 passed |

## 7. Observations (Non-Blocking)

1. **Private attribute access on SimulatedBroker:** `_check_bracket_orders()` accesses `self._broker._pending_brackets` directly (line 429). This is the same pattern used in the Replay Harness and is the only way to inspect pending brackets. Not a bug, but worth noting for future encapsulation if SimulatedBroker adds a public API.

2. **iterrows() in bar loop:** `_run_trading_day` uses `daily_bars.iterrows()` (line 347) for the bar processing loop. This is acceptable for the bar-by-bar fill model (which inherently cannot be vectorized since each bar may change position state), and bar counts per day are small (~390 per symbol x ~10 symbols = ~3,900 rows max).

## 8. Files Changed

- `/Users/stevengizzi/Documents/Coding Projects/argus/argus/backtest/engine.py` — Added `_load_data()`, `_get_daily_bars()`, `_run_trading_day()`, `_check_bracket_orders()`, `_check_time_stop()`, `_publish_fill_events()`. Updated `run()` for day loop.
- `/Users/stevengizzi/Documents/Coding Projects/argus/tests/backtest/test_engine.py` — Added 15 new tests covering day loop, fill model, signal routing, watchlist scoping, and daily state reset.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "summary": "Session 4 implements the bar-level fill model with correct worst-case-for-longs priority (stop > target > time_stop > EOD). All 15 new tests pass. Fill model code paths verified: stop wins when both stop and target trigger; time stop checks for stop hit; targets sorted ascending with freshness guard. No tick synthesis, no asyncio.sleep, no create_task. All do-not-modify files unchanged. Full suite 2,982 passed.",
  "findings": [],
  "escalation_triggers": [],
  "test_results": {
    "session_tests": "29/29 passed",
    "full_suite": "2982 passed, 0 failures"
  }
}
```
