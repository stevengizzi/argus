# Sprint 27.5 Cleanup: Post-Sprint Fixes

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/execution/execution_record.py` (DEF-090 fix target)
   - `argus/analytics/evaluation.py` (type annotation + assert + infinity fixes)
   - `argus/backtest/engine.py` (asyncio deprecation fix)
   - `tests/execution/test_execution_record.py` (test updates for DEF-090)
   - `tests/backtest/test_engine_regime.py` (test updates for async fix)
   - `docs/sprints/sprint-27.5/review-context.md` (sprint constraints reference)
2. Run scoped pre-flight tests:
   ```bash
   python -m pytest tests/execution/test_execution_record.py tests/backtest/test_engine_regime.py tests/analytics/test_evaluation.py -x -v
   ```
   All must pass before starting.
3. Verify you are on the main branch with all S1–S6 commits present.

## Objective
Fix all review findings, cosmetic issues, and DEF-090 from Sprint 27.5 sessions S1–S6. These are surgical, low-risk corrections identified during Tier 2 reviews.

## Fix 1: DEF-090 — `execution_record.py` UTC→ET time_of_day (MEDIUM)

**Problem:** `create_execution_record()` at line 86 stores `time_of_day = fill_timestamp.strftime("%H:%M:%S")`. Since `fill_timestamp` comes from `SystemClock.now()` which returns UTC, the stored `time_of_day` is in UTC — but DEC-061 mandates ET for all market-hours time comparisons, and the slippage model's `_time_bucket()` assumes ET buckets (pre_10am, 10am_2pm, post_2pm ET).

**Fix in `argus/execution/execution_record.py`:**

1. Add import at the top (after existing imports):
   ```python
   from zoneinfo import ZoneInfo
   ```

2. Add module-level constant (after imports, before the dataclass):
   ```python
   _ET = ZoneInfo("America/New_York")
   ```

3. Replace line 86:
   ```python
   # BEFORE:
   time_of_day = fill_timestamp.strftime("%H:%M:%S")
   
   # AFTER:
   time_of_day = fill_timestamp.astimezone(_ET).strftime("%H:%M:%S")
   ```

**Fix in `tests/execution/test_execution_record.py`:**

Update the two `time_of_day` assertions. The test timestamps are March 23, 2026 at UTC 14:30. EDT is active (DST starts March 8, 2026), so UTC 14:30 → ET 10:30.

1. Line 73: `assert record.time_of_day == "14:30:01"` → `assert record.time_of_day == "10:30:01"`
2. Line 165: `assert row["time_of_day"] == "14:30:00"` → `assert row["time_of_day"] == "10:30:00"`

Scan the entire test file for any other `time_of_day` assertions and update them consistently.

**Verification:** `python -m pytest tests/execution/test_execution_record.py -x -v`

## Fix 2: `RegimeMetrics.to_dict()` return type annotation (LOW)

**Problem (S1 F-001):** Return type is `dict[str, float | int]` but the function can return `str` (`"Infinity"`) for the `profit_factor` key.

**Fix in `argus/analytics/evaluation.py`:**

Line 54: Change return type annotation:
```python
# BEFORE:
def to_dict(self) -> dict[str, float | int]:

# AFTER:
def to_dict(self) -> dict[str, float | int | str]:
```

## Fix 3: Replace `assert` with `TypeError` in `from_dict()` (LOW)

**Problem (S1 F-002):** `MultiObjectiveResult.from_dict()` uses `assert isinstance(...)` for type checking at lines 266, 274, 285. These are stripped by `python -O`, which would produce confusing errors instead of clear `TypeError` messages on malformed input.

**Fix in `argus/analytics/evaluation.py`:**

Replace each `assert isinstance(...)` with an explicit `TypeError` raise:

```python
# Line 266:
# BEFORE:
assert isinstance(data_range_raw, list)
# AFTER:
if not isinstance(data_range_raw, list):
    raise TypeError(f"data_range must be a list, got {type(data_range_raw).__name__}")

# Line 274:
# BEFORE:
assert isinstance(regime_raw, dict)
# AFTER:
if not isinstance(regime_raw, dict):
    raise TypeError(f"regime_results must be a dict, got {type(regime_raw).__name__}")

# Line 285:
# BEFORE:
assert isinstance(ci_raw, list)
# AFTER:
if not isinstance(ci_raw, list):
    raise TypeError(f"confidence_interval must be a list, got {type(ci_raw).__name__}")
```

## Fix 4: Negative infinity serialization roundtrip (NEGLIGIBLE)

**Problem (S1 review observation):** `math.isinf()` returns True for both `+inf` and `-inf`. Negative infinity would serialize as `"Infinity"` and deserialize as positive infinity, losing the sign. While `profit_factor` is inherently non-negative, correctness demands the roundtrip be lossless for all float values.

**Fix in `argus/analytics/evaluation.py`:**

This affects 4 locations — both `to_dict` and `from_dict` in both `RegimeMetrics` and `MultiObjectiveResult`.

**RegimeMetrics.to_dict()** — replace the profit_factor serialization:
```python
# BEFORE:
"profit_factor": "Infinity" if math.isinf(pf) else pf,

# AFTER:
"profit_factor": "Infinity" if pf == float("inf") else ("-Infinity" if pf == float("-inf") else pf),
```

**RegimeMetrics.from_dict()** — replace the profit_factor deserialization:
```python
# BEFORE:
profit_factor = float("inf") if pf == "Infinity" else float(pf)

# AFTER:
profit_factor = float("inf") if pf == "Infinity" else (float("-inf") if pf == "-Infinity" else float(pf))
```

**MultiObjectiveResult.to_dict()** — same change for the profit_factor line:
```python
# BEFORE:
"profit_factor": "Infinity" if math.isinf(pf) else pf,

# AFTER:
"profit_factor": "Infinity" if pf == float("inf") else ("-Infinity" if pf == float("-inf") else pf),
```

**MultiObjectiveResult.from_dict()** — same change:
```python
# BEFORE:
profit_factor = float("inf") if pf_raw == "Infinity" else float(pf_raw)

# AFTER:
profit_factor = float("inf") if pf_raw == "Infinity" else (float("-inf") if pf_raw == "-Infinity" else float(pf_raw))
```

**Add test** in `tests/analytics/test_evaluation.py`:
```python
def test_regime_metrics_serialization_negative_infinity():
    """Negative infinity roundtrips correctly."""
    rm = RegimeMetrics(
        sharpe_ratio=-1.0,
        max_drawdown_pct=-0.5,
        profit_factor=float("-inf"),
        win_rate=0.0,
        total_trades=5,
        expectancy_per_trade=-2.0,
    )
    d = rm.to_dict()
    assert d["profit_factor"] == "-Infinity"
    restored = RegimeMetrics.from_dict(d)
    assert restored.profit_factor == float("-inf")
```

## Fix 5: `asyncio.get_event_loop()` deprecation in `_load_spy_daily_bars` (LOW)

**Problem (S2 F-002):** `_load_spy_daily_bars()` uses `asyncio.get_event_loop().run_until_complete()` to call the async `feed.load()`. This is deprecated in Python 3.12+ and is fundamentally unsafe when called from within a running event loop (which `to_multi_objective_result` has, since it's `async def` and uses `await` for the trade logger query). Current tests work only because they mock `_load_spy_daily_bars` before the real code is reached.

**Fix in `argus/backtest/engine.py`:**

Make `_load_spy_daily_bars` async and use `await` directly:

1. Change the method signature:
   ```python
   # BEFORE:
   def _load_spy_daily_bars(
       self, start_date: date, end_date: date,
   ) -> pd.DataFrame | None:
   
   # AFTER:
   async def _load_spy_daily_bars(
       self, start_date: date, end_date: date,
   ) -> pd.DataFrame | None:
   ```

2. Replace the `get_event_loop` / `run_until_complete` block with a direct `await`:
   ```python
   # BEFORE:
   loop = asyncio.get_event_loop()
   data = loop.run_until_complete(
       feed.load(["SPY"], margin_start, end_date)
   )
   
   # AFTER:
   data = await feed.load(["SPY"], margin_start, end_date)
   ```

3. Update the caller in `to_multi_objective_result()`:
   ```python
   # BEFORE:
   daily_bars = self._load_spy_daily_bars(
       result.start_date, result.end_date
   )
   
   # AFTER:
   daily_bars = await self._load_spy_daily_bars(
       result.start_date, result.end_date
   )
   ```

**Fix in `tests/backtest/test_engine_regime.py`:**

1. `test_spy_daily_bar_aggregation` (currently sync, ~line 151):
   - Add `@pytest.mark.asyncio` decorator
   - Change `def test_spy_daily_bar_aggregation(tmp_path: Path) -> None:` → `async def test_spy_daily_bar_aggregation(tmp_path: Path) -> None:`
   - Change `daily = engine._load_spy_daily_bars(...)` → `daily = await engine._load_spy_daily_bars(...)`

2. `test_load_spy_daily_bars_no_spy_dir` (currently sync, ~line 457):
   - Add `@pytest.mark.asyncio` decorator
   - Change `def` → `async def`
   - Change `result = engine._load_spy_daily_bars(...)` → `result = await engine._load_spy_daily_bars(...)`

3. All `patch.object(engine, "_load_spy_daily_bars", return_value=X)` calls — these create `MagicMock` objects which are not awaitable. Replace with `AsyncMock`:

   For each occurrence (approximately lines 263, 317, 327, 366, 417), change:
   ```python
   # BEFORE:
   with patch.object(engine, "_load_spy_daily_bars", return_value=X):
   
   # AFTER:
   with patch.object(engine, "_load_spy_daily_bars", new=AsyncMock(return_value=X)):
   ```

   `AsyncMock` is already imported in this test file (line 11).

4. The test at `test_to_multi_objective_result_no_spy` (~line 373) calls the real `_load_spy_daily_bars` (no mock) — since the SPY cache dir doesn't exist, it returns None naturally. With the async change, the `await` call will work correctly since the test already runs in an async context (`@pytest.mark.asyncio`). No change needed for this test.

**Verification:**
```bash
python -m pytest tests/backtest/test_engine_regime.py -x -v
python -m pytest tests/integration/test_evaluation_pipeline.py -x -v
```

## Constraints
- Do NOT modify any strategy files, frontend files, or API route files.
- Do NOT modify `backtest/metrics.py`, `backtest/walk_forward.py`, `core/regime.py`, or `analytics/performance.py`.
- Do NOT add new files (except tests if needed).
- Do NOT change any public API signatures (only `_load_spy_daily_bars` which is a private method).
- Do NOT introduce new Python package dependencies.

## Test Targets
After all fixes:
1. All existing tests must still pass: `python -m pytest --ignore=tests/test_main.py -n auto -q`
2. Scoped verification:
   ```bash
   python -m pytest tests/execution/test_execution_record.py tests/backtest/test_engine_regime.py tests/analytics/test_evaluation.py tests/integration/test_evaluation_pipeline.py -x -v
   ```
3. New test added: `test_regime_metrics_serialization_negative_infinity` (1 new test minimum)
4. Import check: `python -c "from argus.analytics.evaluation import MultiObjectiveResult; from argus.backtest.engine import BacktestEngine; from argus.execution.execution_record import create_execution_record"`

## Definition of Done
- [ ] All 5 fixes implemented
- [ ] All existing tests pass (no regressions)
- [ ] New negative-infinity roundtrip test passes
- [ ] No circular import issues
- [ ] Close-out report written to `docs/sprints/sprint-27.5/cleanup-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-27.5/cleanup-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.5/cleanup-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped): `python -m pytest tests/execution/test_execution_record.py tests/backtest/test_engine_regime.py tests/analytics/test_evaluation.py tests/integration/test_evaluation_pipeline.py -x -v`
5. Files that should NOT have been modified: `backtest/metrics.py`, `backtest/walk_forward.py`, `core/regime.py`, `analytics/performance.py`, all strategy files, all frontend files, all API routes

## Session-Specific Review Focus (for @reviewer)
1. Verify `time_of_day` now stores ET, not UTC — check the `astimezone(_ET)` call
2. Verify test assertions updated to match ET conversion (UTC 14:30 → ET 10:30 for March dates)
3. Verify `RegimeMetrics.to_dict()` return type includes `str`
4. Verify all 3 `assert isinstance` replaced with `if not isinstance: raise TypeError`
5. Verify negative infinity roundtrip works in both `RegimeMetrics` and `MultiObjectiveResult`
6. Verify `_load_spy_daily_bars` is now `async def` with `await feed.load()`
7. Verify all `patch.object` mocks for `_load_spy_daily_bars` use `AsyncMock`
8. Verify no `asyncio.get_event_loop()` remains in engine.py
9. Verify no regression in existing BacktestEngine tests