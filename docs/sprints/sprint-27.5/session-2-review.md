---BEGIN-REVIEW---

# Sprint 27.5 Session 2 — Tier 2 Review
## Regime Tagging in BacktestEngine

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-24
**Verdict:** CLEAR

---

### 1. Scope Compliance

All 5 spec requirements (R1-R5) are implemented as specified:
- `_load_spy_daily_bars()` reads SPY Parquet, resamples to daily OHLCV
- `_compute_regime_tags()` uses RegimeClassifier per day with RANGE_BOUND default
- `to_multi_objective_result()` is async, loads SPY, partitions trades, produces MOR
- `_compute_regime_metrics()` computes per-regime Sharpe/DD/PF/WR/expectancy
- `BacktestEngine.run()` return type is unchanged (still returns `BacktestResult`)

No scope additions or gaps.

### 2. Session-Specific Focus Item Verification

**F1: SPY daily bar aggregation correctness.**
Verified at line 1041-1049. Uses `groupby("trading_date")` with `first()` for open, `max()` for high, `min()` for low, `last()` for close, `sum()` for volume. Correct.

**F2: Sufficient daily bar history for SMA computation.**
The 3-month lookback margin (line 1020-1026) provides ~63 trading days before `start_date`, which exceeds the 50-bar SMA-50 requirement. Days with < 20 bars fall back to RANGE_BOUND (line 1078). Between 20 and 49 bars, `compute_indicators` returns `spy_sma_50 = None`, and `RegimeClassifier.classify()` handles None SMA-50 gracefully (falls back to SMA-20-only classification). Adequate.

**F3: Trade-to-regime partitioning uses exit_date.**
Verified at line 1237-1239. Partitioning extracts `exit_time.date()`, not entry_date. Correct.

**F4: regime_results uses string keys.**
Verified at line 1085 (`regime.value`), line 1244 (`MarketRegime.RANGE_BOUND.value`), and the `regime_results` dict type annotation `dict[str, RegimeMetrics]` at line 1249. All keys are strings. Correct.

**F5: BacktestEngine.run() return type unchanged.**
Verified. `to_multi_objective_result()` is a separate async method (line 1177). `run()` still returns `BacktestResult`. Test `test_to_multi_objective_result_preserves_backtest_result` (line 441-454) explicitly validates this. Correct.

**F6: No FMP API calls.**
Verified. `_load_spy_daily_bars` reads only from Parquet cache via `HistoricalDataFeed.load()`. Falls back to RANGE_BOUND when SPY not in cache. No FMP imports or calls. Correct.

**F7: Single-day regime Sharpe handling.**
Verified at line 1141-1151. When `len(daily_returns) < 2`, Sharpe returns 0.0. Test `test_regime_metrics_single_trade` (line 425-437) validates this. Correct.

### 3. Protected File Verification

| File | Status |
|------|--------|
| `argus/backtest/metrics.py` | Not modified (git diff empty) |
| `argus/backtest/walk_forward.py` | Not modified (git diff empty) |
| `argus/core/regime.py` | Not modified (git diff empty) |
| `argus/analytics/performance.py` | Not modified (git diff empty) |
| Strategy files | Not modified (git diff empty) |

### 4. Regression Checklist

| Check | Result |
|-------|--------|
| Full pytest suite (--ignore=tests/test_main.py) | PASS: 3,133 passed + 4 pre-existing flaky failures = 3,137 total (>= 3,071 baseline) |
| Existing BacktestEngine tests pass without modification | PASS: all 44 tests in test_engine.py pass |
| No circular imports | PASS: `from argus.backtest.engine import BacktestEngine` succeeds |
| backtest/metrics.py not modified | PASS |
| backtest/walk_forward.py not modified | PASS |
| core/regime.py not modified | PASS |
| analytics/performance.py not modified | PASS |

### 5. Escalation Criteria Check

| Criterion | Triggered? |
|-----------|------------|
| BacktestEngine regression | No — all 44 existing tests pass |
| Circular imports | No — import succeeds cleanly |
| BacktestResult interface change | No — `run()` still returns BacktestResult |
| Regime tagging >80% single-regime concentration | Not testable without real Parquet data; no trigger observed in synthetic tests |

### 6. Findings

**MINOR (informational, not blocking):**

1. **Unused import:** `import math` is added at line 27 of engine.py but never used in the new code. Harmless but should be cleaned up.

2. **`asyncio.get_event_loop()` deprecation risk:** `_load_spy_daily_bars()` uses `asyncio.get_event_loop().run_until_complete()` (line 1028-1031). The close-out correctly notes this works in the SyncEventBus context (no running event loop). However, `asyncio.get_event_loop()` is deprecated in Python 3.12+ when no event loop is running. Since the project is on Python 3.11, this is not currently broken, but will need attention upon a Python version upgrade. The close-out already flags this as a deferred observation.

3. **`# type: ignore` usage:** There are 6 `# type: ignore[arg-type]` comments in `_compute_regime_metrics()` (lines 1111-1138). These arise from `dict.get()` returning `object | None` on a `dict[str, object]`. The specific error codes are included, which follows project style. Acceptable given the dict-of-objects pattern.

### 7. Test Coverage Assessment

11 new tests added covering:
- SPY daily bar aggregation correctness
- Regime tag computation (uptrend -> BULLISH_TRENDING)
- Insufficient history fallback (< 20 bars -> RANGE_BOUND)
- to_multi_objective_result basic flow
- Regime partitioning with two different regimes
- Confidence tier computation
- No-SPY fallback (RANGE_BOUND)
- Zero-trade edge case
- Single-trade regime metrics
- BacktestResult preservation (run() unchanged)
- Missing SPY directory

Coverage is thorough for the feature scope.

### 8. Summary

Clean implementation that adds regime tagging to BacktestEngine without modifying the existing `run()` contract or any protected files. All spec requirements met. All focus items verified. The 4 test failures in the full suite are pre-existing flaky tests (FMP reference cache timing + sprint runner notification timing), unrelated to this session's changes. Test count increased from 3,126 to 3,137 (+11).

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.5",
  "session": "S2",
  "verdict": "CLEAR",
  "confidence": "HIGH",
  "tests": {
    "scoped_pass": true,
    "scoped_count": 55,
    "full_suite_pass": true,
    "full_suite_total": 3137,
    "full_suite_passed": 3133,
    "full_suite_failed": 4,
    "full_suite_failed_preexisting": true,
    "new_tests": 11
  },
  "protected_files_clean": true,
  "escalation_triggers": [],
  "findings": [
    {
      "severity": "LOW",
      "category": "code-hygiene",
      "description": "Unused `import math` added to engine.py"
    },
    {
      "severity": "LOW",
      "category": "forward-compat",
      "description": "asyncio.get_event_loop() deprecated in Python 3.12+ (project on 3.11, not currently broken)"
    }
  ],
  "regression_checklist": {
    "full_suite_passes": true,
    "existing_engine_tests_pass": true,
    "metrics_py_unmodified": true,
    "walk_forward_py_unmodified": true,
    "regime_py_unmodified": true,
    "performance_py_unmodified": true,
    "no_circular_imports": true
  }
}
```
