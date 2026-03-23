# Sprint 27.5, Session 2: Regime Tagging in BacktestEngine

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/analytics/evaluation.py` (S1 output — MultiObjectiveResult, RegimeMetrics, compute_confidence_tier)
   - `argus/backtest/engine.py` (BacktestEngine — the file you'll modify)
   - `argus/core/regime.py` (RegimeClassifier, RegimeIndicators, MarketRegime)
   - `argus/backtest/historical_data_feed.py` (Parquet cache access patterns)
   - `docs/sprints/sprint-27.5/review-context.md`
2. Run scoped test baseline (DEC-328 — session 2+):
   ```bash
   python -m pytest tests/backtest/test_engine.py tests/analytics/test_evaluation.py -x -q
   ```
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify S1 is committed and `argus/analytics/evaluation.py` exists

## Objective
Make BacktestEngine produce regime-tagged results by aggregating SPY daily bars from the Parquet cache, running RegimeClassifier per trading day, partitioning trades by regime, and exposing `to_multi_objective_result()`.

## Requirements

1. In `argus/backtest/engine.py`, add a method to **aggregate SPY daily bars from the Parquet cache**:
   - Method: `_load_spy_daily_bars(self, start_date: date, end_date: date) → pd.DataFrame | None`
   - Read SPY 1-minute Parquet files from the same `data_dir` used by `HistoricalDataFeed`
   - Resample to daily OHLCV: group by date, take first open, max high, min low, last close, sum volume
   - Return DataFrame with columns: `open`, `high`, `low`, `close`, `volume`, indexed by date
   - Return `None` if SPY not found in cache (trigger fallback)

2. In `argus/backtest/engine.py`, add a method to **tag each trading day with a regime**:
   - Method: `_compute_regime_tags(self, daily_bars: pd.DataFrame) → dict[date, str]`
   - Instantiate `RegimeClassifier` (import from `argus.core.regime`)
   - For each date, compute `RegimeIndicators` from the daily bar DataFrame (using the RegimeClassifier's `compute_indicators()` method which takes a DataFrame of daily bars)
   - Call `classify()` to get `MarketRegime`
   - Return `{date: regime.value}` (string values, not enum)
   - If daily_bars has insufficient history for SMA computation on early dates, use `RANGE_BOUND` as default

3. In `argus/backtest/engine.py`, add **`to_multi_objective_result()`**:
   - Method: `async def to_multi_objective_result(self, result: BacktestResult, parameter_hash: str = "", wfe: float = 0.0, is_oos: bool = False) → MultiObjectiveResult`
   - Load SPY daily bars → compute regime tags
   - Partition trades by exit_date → regime tag
   - For each regime with trades: compute `RegimeMetrics` (Sharpe, drawdown, PF, win rate, trades, expectancy from that subset)
   - Compute `ConfidenceTier` from total trades and regime trade counts
   - Call `from_backtest_result()` with the regime results and confidence data
   - If SPY daily bars unavailable: log WARNING, assign all days RANGE_BOUND, still produce valid MOR with single-regime breakdown

4. In `argus/backtest/engine.py`, **store regime tag data** during `run()`:
   - After the backtest run completes, store the list of `(trade, exit_date)` pairs so `to_multi_objective_result()` can partition them
   - Store as `self._completed_trades: list[Trade]` (populated from trade logger query at end of run)
   - This is lazy — only populated if `to_multi_objective_result()` is called

5. **Per-regime metric computation** helper:
   - Method: `_compute_regime_metrics(self, trades: list[Trade]) → RegimeMetrics`
   - Reuse the same metric computation logic from `backtest/metrics.py` (shared module) for the trade subset
   - Handle edge case: 0 trades → skip (don't include this regime in results)
   - Handle edge case: 1 trade → compute what's possible (win_rate = 1.0 or 0.0, Sharpe = 0.0, etc.)

## Constraints
- Do NOT modify `argus/backtest/metrics.py` — use the shared `compute_metrics` from `argus/analytics/performance.py` for per-regime calculation, or compute inline
- Do NOT modify `argus/core/regime.py`
- Do NOT modify `argus/backtest/config.py` in this session (S6 handles config)
- Do NOT add FMP API calls in this session — Parquet-first with RANGE_BOUND fallback is sufficient. FMP fallback can be added as a future enhancement.
- `to_multi_objective_result()` is async because it queries trades from the TradeLogger (which is async)

## Test Targets
After implementation:
- Existing BacktestEngine tests: all must still pass without modification
- New tests in `tests/backtest/test_engine_regime.py`:
  1. `test_spy_daily_bar_aggregation` — synthetic 1-min bars → correct daily OHLCV
  2. `test_regime_tag_computation` — known daily bars → correct MarketRegime assignment
  3. `test_regime_tag_insufficient_history` — early dates → RANGE_BOUND default
  4. `test_to_multi_objective_result_basic` — BacktestEngine run with test data → valid MOR with regime_results
  5. `test_to_multi_objective_result_regime_partitioning` — trades on different regime days → correct partition
  6. `test_to_multi_objective_result_confidence_tier` — tier computed from actual regime distribution
  7. `test_to_multi_objective_result_no_spy` — SPY not in cache → WARNING + single RANGE_BOUND regime
  8. `test_to_multi_objective_result_zero_trades` — empty backtest → MOR with ENSEMBLE_ONLY
  9. `test_regime_metrics_single_trade` — one trade in a regime → valid (degenerate) RegimeMetrics
  10. `test_to_multi_objective_result_preserves_backtest_result` — BacktestEngine.run() return unchanged
- Minimum new test count: 8
- Test command: `python -m pytest tests/backtest/test_engine_regime.py tests/backtest/test_engine.py -x -v`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing BacktestEngine tests pass without modification
- [ ] New tests written and passing (≥8)
- [ ] `BacktestEngine.run()` return type and behavior unchanged
- [ ] `to_multi_objective_result()` produces valid MOR with populated regime_results
- [ ] Close-out report written to `docs/sprints/sprint-27.5/session-2-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| BacktestEngine.run() unchanged | Existing tests in test_engine.py all pass |
| No BacktestResult modification | `git diff argus/backtest/metrics.py` is empty |
| No RegimeClassifier modification | `git diff argus/core/regime.py` is empty |
| No circular imports | `python -c "from argus.backtest.engine import BacktestEngine"` succeeds |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-27.5/session-2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-27.5/review-context.md`
2. Close-out: `docs/sprints/sprint-27.5/session-2-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped): `python -m pytest tests/backtest/test_engine_regime.py tests/backtest/test_engine.py -x -v`
5. Files NOT modified: `argus/backtest/metrics.py`, `argus/backtest/walk_forward.py`, `argus/core/regime.py`, `argus/analytics/performance.py`, all strategy files

Write review to: `docs/sprints/sprint-27.5/session-2-review.md`

## Post-Review Fix Documentation
If CONCERNS → fix and update both close-out and review files per template.

## Session-Specific Review Focus (for @reviewer)
1. Verify SPY daily bar aggregation is correct (first open, max high, min low, last close, sum volume)
2. Verify RegimeClassifier receives sufficient daily bar history for SMA computation (at least 50 bars before the first tagged date)
3. Verify trade-to-regime partitioning uses exit_date (not entry_date) — trades are attributed to the day they closed
4. Verify regime_results uses string keys (`regime.value`), not MarketRegime enum instances
5. Verify BacktestEngine.run() return type is unchanged — `to_multi_objective_result()` is a separate call
6. Verify no FMP API calls (Parquet-only with RANGE_BOUND fallback)
7. Verify per-regime Sharpe computation handles single-day regimes (1 return → Sharpe = 0.0)

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Full pytest suite passes with `--ignore=tests/test_main.py` (≥3,071 pass, 0 fail)
- [ ] Existing BacktestEngine tests pass without modification
- [ ] `backtest/metrics.py` not modified
- [ ] `backtest/walk_forward.py` not modified
- [ ] `core/regime.py` not modified
- [ ] No circular imports among analytics/backtest modules

## Sprint-Level Escalation Criteria (for @reviewer)
**Hard Stops:** BacktestEngine regression, circular imports, BacktestResult interface change.
**Escalate to Tier 3:** Regime tagging >80% single-regime concentration with real Parquet data.
