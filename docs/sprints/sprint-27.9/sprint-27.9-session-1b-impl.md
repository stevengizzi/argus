# Sprint 27.9, Session 1b: yfinance Integration + Derived Metrics

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/data/vix_data_service.py` (Session 1a output)
   - `argus/data/vix_config.py` (Session 1a output)
   - `config/vix_regime.yaml`
2. Run scoped test baseline (DEC-328):
   ```bash
   python -m pytest tests/data/test_vix_data_service.py -x -q
   ```
   Expected: 5 tests, all passing (confirmed by Session 1a close-out)
3. Install yfinance: `pip install yfinance --break-system-packages`

## Objective
Wire yfinance into VIXDataService for historical backfill and incremental updates. Implement all 5 derived metric computations. Add daily update asyncio task.

## Requirements

1. **Modify `argus/data/vix_data_service.py`** (~80 additional lines):
   - `fetch_historical(years: int) -> pd.DataFrame`: Download ^VIX and ^GSPC daily OHLCV from yfinance for `years` back. Merge on date. Return raw DataFrame. Handle: yfinance returning empty DataFrame (raise `VIXDataUnavailable` exception), partial data (log WARNING, proceed with available).
   - `fetch_incremental(last_date: date) -> pd.DataFrame`: Download from `last_date + 1 day` to today. Same error handling.
   - `compute_derived_metrics(df: pd.DataFrame) -> pd.DataFrame`: Add 5 computed columns:
     - `vol_of_vol_ratio`: rolling σ₁₀(VIX close) / rolling σ₆₀(VIX close). Guard σ₆₀ = 0 with epsilon (1e-10).
     - `vix_percentile`: rolling 252-day percentile rank of VIX close. `df['vix_close'].rolling(252).apply(lambda x: percentileofscore(x, x.iloc[-1]) / 100.0)`. Return None for rows with < 252 history.
     - `term_structure_proxy`: VIX close / rolling 63-day MA of VIX close. Guard MA = 0.
     - `realized_vol_20d`: annualized 20-day rolling std of SPX log returns. `np.log(spx_close / spx_close.shift(1)).rolling(20).std() * np.sqrt(252)`.
     - `variance_risk_premium`: `(vix_close / 100)² * 252 - realized_vol_20d²`. Note: VIX is quoted in percentage points, so VIX=20 means 20% annualized implied vol. Adjust formula: `(vix_close**2) - ((realized_vol_20d * 100)**2)`. Actually, simplest: VRP = VIX² − (RV₂₀ × 100)² where both are in percentage-point units. Verify units in tests.
   - `initialize() -> None`: Async method. If SQLite has data, load it (trust-cache-on-startup). Compute how many days are missing. If missing > 0 and ≤ 30, run `fetch_incremental()`. If missing > 30 or no data, run `fetch_historical()`. Compute derived metrics. Persist. Set `_is_ready = True`.
   - `_start_daily_update_task()`: asyncio task that runs `fetch_incremental()` + `compute_derived_metrics()` + `persist_daily()` every `update_interval_seconds` during US market hours (9:30–16:15 ET). Market hours check using existing ARGUS patterns.
   - Custom exception: `VIXDataUnavailable(Exception)`.

2. **Create `tests/data/test_vix_derived_metrics.py`** (7 tests):
   - `test_vol_of_vol_ratio_known_values`: Synthetic VIX series with known σ₁₀ and σ₆₀ → verify ratio.
   - `test_vix_percentile_known_values`: Sorted synthetic series → verify percentile.
   - `test_term_structure_proxy_known_values`: Constant VIX → proxy = 1.0. Rising VIX → proxy > 1.0.
   - `test_realized_vol_known_values`: Synthetic SPX with constant daily returns → verify annualized vol.
   - `test_vrp_known_values`: VIX=20, RV=15% → VRP = 400 - 225 = 175. Verify.
   - `test_sigma60_zero_guard`: Series where σ₆₀ would be 0 → vol_of_vol_ratio returns None, logs WARNING.
   - `test_incremental_update`: Persist initial data, fetch incremental (mock yfinance), verify only new rows added.

## Constraints
- Do NOT modify: any files outside `argus/data/vix_data_service.py` and test files
- Do NOT add yfinance to a requirements.txt yet (note as DEF if one exists)
- Mock yfinance in tests — do NOT make real API calls in pytest. Use `unittest.mock.patch("yfinance.download")` with synthetic DataFrames.
- One integration test may optionally call real yfinance (marked `@pytest.mark.integration` and skipped by default).

## Test Targets
- Existing tests: all must still pass
- New tests: 7 in `tests/data/test_vix_derived_metrics.py`
- Minimum new test count: 7
- Test command: `python -m pytest tests/data/test_vix_data_service.py tests/data/test_vix_derived_metrics.py -x -q`

## Definition of Done
- [ ] yfinance fetch_historical and fetch_incremental implemented
- [ ] All 5 derived metrics compute correctly with known inputs
- [ ] Edge cases guarded (σ₆₀=0, insufficient history, empty yfinance response)
- [ ] initialize() method with trust-cache-on-startup pattern
- [ ] Daily update asyncio task with market hours guard
- [ ] 7 new tests written and passing (mocked yfinance)
- [ ] All existing tests pass
- [ ] Close-out report written to `docs/sprints/sprint-27.9/session-1b-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Session 1a tests still pass | `python -m pytest tests/data/test_vix_data_service.py -x -q` |
| No import errors | `python -c "from argus.data.vix_data_service import VIXDataService"` |

## Close-Out
Follow the close-out skill in .claude/skills/close-out.md. Write to: `docs/sprints/sprint-27.9/session-1b-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide @reviewer with:
1. Review context: `docs/sprints/sprint-27.9/review-context.md`
2. Close-out: `docs/sprints/sprint-27.9/session-1b-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/data/test_vix_data_service.py tests/data/test_vix_derived_metrics.py -x -q`
5. Do-not-modify: `argus/core/`, `argus/strategies/`, `argus/execution/`, `argus/backtest/`, `argus/ai/`, `argus/config/`

## Post-Review Fix Documentation
If @reviewer reports CONCERNS, fix and update both close-out and review report files.

## Session-Specific Review Focus (for @reviewer)
1. Verify VRP formula units are consistent (VIX in % points, RV in % points)
2. Verify σ₆₀=0 guard uses epsilon, not division-by-zero exception
3. Verify yfinance is mocked in ALL pytest tests (no real API calls)
4. Verify initialize() loads from SQLite FIRST, then fetches missing (trust-cache)
5. Verify daily task has market hours guard

## Sprint-Level Regression Checklist (for @reviewer)
R1–R15 as listed in review-context.md. R13 is primary for this session.

## Sprint-Level Escalation Criteria (for @reviewer)
1–7 as listed in review-context.md.
