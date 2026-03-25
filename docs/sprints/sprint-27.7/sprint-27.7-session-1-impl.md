# Sprint 27.7, Session 1: Core Model + Tracker Logic + Shared Fill Model

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/events.py` (SignalEvent, CandleEvent, OrderRejectedEvent)
   - `argus/core/regime.py` (RegimeVector dataclass — lines 82–155)
   - `argus/backtest/engine.py` (fill logic in `_process_bar_for_position()` — lines 550–614, and `_check_time_stop()` — lines 616–670)
   - `argus/data/intraday_candle_store.py` (public API: `get_bars()`, `get_latest()`, `has_bars()`)
   - `argus/strategies/telemetry.py` (EvaluationEvent, EvaluationEventType — pattern reference)
2. Run the test baseline (DEC-328 — Session 1, full suite):
   ```
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```
   Expected: ~3,412 tests, all passing (tolerance ±50)
3. Verify you are on branch `main` (or create feature branch `sprint-27.7`)

## Objective
Extract the bar-level fill priority logic from BacktestEngine into a shared `TheoreticalFillModel`, then build the `CounterfactualPosition` model and `CounterfactualTracker` core logic including IntradayCandleStore backfill at position open.

## Requirements

### 1. Create `argus/core/fill_model.py` — Shared TheoreticalFillModel

This module extracts the fill priority logic currently embedded in BacktestEngine's `_process_bar_for_position()`. Both BacktestEngine and CounterfactualTracker will call this code.

1a. Define `ExitReason` enum (StrEnum):
    - `STOPPED_OUT` — bar low breached stop price
    - `TARGET_HIT` — bar high breached target price
    - `TIME_STOPPED` — time stop duration exceeded
    - `EOD_CLOSED` — end-of-day forced close
    - `EXPIRED` — no data received within timeout (counterfactual-specific, not used by BacktestEngine)

1b. Define `ExitResult` frozen dataclass:
    - `exit_reason: ExitReason`
    - `exit_price: float`

1c. Define `evaluate_bar_exit()` pure function:
    ```python
    def evaluate_bar_exit(
        bar_high: float,
        bar_low: float,
        bar_close: float,
        stop_price: float,
        target_price: float,
        time_stop_expired: bool,
    ) -> ExitResult | None:
    ```
    Fill priority (worst-case-for-longs):
    1. If `bar_low <= stop_price` → `ExitResult(STOPPED_OUT, stop_price)`
    2. Elif `bar_high >= target_price` → `ExitResult(TARGET_HIT, target_price)`
    3. Elif `time_stop_expired` → check if stop also hit on this bar (`bar_low <= stop_price` → use stop_price), else `ExitResult(TIME_STOPPED, bar_close)`
    4. Else → `None` (no exit on this bar)

    Note: This is the exact logic from BacktestEngine lines 587–614. The time stop case at priority 3 handles the edge case where the time stop bar also breaches the stop — use the stop price (worst case for longs).

### 2. Refactor `argus/backtest/engine.py` — Use shared fill model

2a. In `_process_bar_for_position()`, replace the inline fill priority logic with a call to `fill_model.evaluate_bar_exit()`. The method's overall structure (collecting pending brackets, iterating targets, calling `_check_time_stop`) should remain largely unchanged — the fill decision for each bracket is what moves to the shared function.

2b. This is a behavior-preserving refactor. After the change, running any backtest should produce identical results. Add a regression test (see Test Targets).

### 3. Create `argus/intelligence/counterfactual.py` — Core model and tracker

3a. Define `RejectionStage` enum (StrEnum):
    - `QUALITY_FILTER` — Quality Engine grade below minimum
    - `POSITION_SIZER` — Dynamic sizer returned 0 shares
    - `RISK_MANAGER` — Risk Manager rejected the signal
    - `SHADOW` — Shadow-mode strategy (signal was never intended for execution)

3b. Define `CounterfactualPosition` frozen dataclass:
    ```
    Fields:
      # Identity
      position_id: str (ULID)
      
      # Signal data (copied from SignalEvent)
      symbol: str
      strategy_id: str
      entry_price: float
      stop_price: float
      target_price: float  # T1 only — first element of signal.target_prices
      time_stop_seconds: int | None
      
      # Rejection metadata
      rejection_stage: RejectionStage
      rejection_reason: str
      quality_score: float | None
      quality_grade: str | None
      regime_vector_snapshot: dict | None  # RegimeVector.to_dict() at rejection time
      signal_metadata: dict  # signal.signal_context + any additional metadata
      
      # Timing
      opened_at: datetime  # ET naive, per DEC-276
      closed_at: datetime | None
      
      # Outcome (populated on close)
      exit_price: float | None
      exit_reason: ExitReason | None
      theoretical_pnl: float | None  # exit_price - entry_price (for LONG)
      theoretical_r_multiple: float | None  # pnl / (entry_price - stop_price)
      duration_seconds: float | None
      
      # Tracking (updated on each bar)
      max_adverse_excursion: float  # Worst drawdown from entry (always >= 0)
      max_favorable_excursion: float  # Best unrealized gain from entry (always >= 0)
      bars_monitored: int  # Number of candles processed
    ```

    Note: `CounterfactualPosition` is frozen except for monitoring fields. Use a mutable tracking wrapper or a separate mutable state object alongside the frozen position. One pattern: the tracker holds a `dict[str, _MonitoringState]` keyed by position_id for the mutable MAE/MFE/bars_monitored, and the frozen position is only created on close with final values.

3c. Define `CounterfactualTracker` class:
    ```python
    class CounterfactualTracker:
        def __init__(self, candle_store=None, eod_close_time="16:00", no_data_timeout_seconds=300):
            ...
        
        def track(self, signal: SignalEvent, rejection_reason: str, 
                  rejection_stage: RejectionStage, metadata: dict | None = None) -> str:
            """Open a counterfactual position. Returns position_id (ULID).
            
            Immediately queries IntradayCandleStore for historical bars since
            entry_time and processes them. If the position would already be
            closed (e.g., stop breached before rejection point), it's marked
            closed immediately.
            """
        
        async def on_candle(self, event: CandleEvent) -> None:
            """Process a candle for all open positions on this symbol.
            Uses evaluate_bar_exit() from fill_model. Updates MAE/MFE."""
        
        async def close_all_eod(self) -> None:
            """Close all remaining open positions at EOD. Mark-to-market at
            last known price or bar close."""
        
        def check_timeouts(self) -> list[str]:
            """Check for positions that haven't received data within timeout.
            Returns list of expired position_ids."""
        
        def get_open_positions(self) -> list[...]:
            """Return all currently monitored positions."""
        
        def get_closed_positions(self, since: datetime | None = None) -> list[...]:
            """Return closed positions, optionally filtered by close time."""
    ```

    Key implementation details:
    - Use T1 only: `target_price = signal.target_prices[0]` (guard for empty tuple — skip if no targets).
    - IntradayCandleStore backfill: In `track()`, if `self._candle_store` is not None and `has_bars(symbol)`, call `get_bars(symbol, start=signal.timestamp, end=now)` and process each bar through `evaluate_bar_exit()`. If any bar triggers an exit, close immediately.
    - Time stop tracking: Record `opened_at` timestamp. On each candle, check if `(candle.timestamp - opened_at).total_seconds() >= time_stop_seconds`. If yes, pass `time_stop_expired=True` to `evaluate_bar_exit()`.
    - MAE/MFE: On each bar, `mae = max(mae, entry_price - bar_low)` and `mfe = max(mfe, bar_high - entry_price)` for LONG positions.
    - Internal storage: `_open_positions: dict[str, _OpenPosition]` (mutable monitoring state) keyed by position_id. `_closed_positions: list[CounterfactualPosition]` (or similar). Separate `_symbols_to_positions: dict[str, set[str]]` for O(1) candle routing.

## Constraints
- Do NOT modify: `argus/core/risk_manager.py`, `argus/core/regime.py`, `argus/data/intraday_candle_store.py`, `argus/core/events.py` (event changes come in S3a), `argus/main.py` (wiring comes in S3a/S3b), any strategy files, any frontend files
- Do NOT change: BacktestEngine's external API or behavior — the refactor is internal only
- Do NOT add: SQLite persistence (Session 2), event bus subscriptions (Session 3b), config models (Session 2)
- The tracker in this session operates standalone — it's called directly via `tracker.track()` in tests. Event bus wiring comes later.

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **fill_model: stop triggers** — bar_low <= stop_price → STOPPED_OUT at stop_price
  2. **fill_model: target triggers** — bar_high >= target_price → TARGET_HIT at target_price
  3. **fill_model: both trigger, stop wins** — bar_low <= stop AND bar_high >= target → STOPPED_OUT
  4. **fill_model: time stop** — time_stop_expired=True, bar doesn't hit stop → TIME_STOPPED at bar_close
  5. **fill_model: time stop + stop breach** — time_stop_expired=True, bar_low <= stop → STOPPED_OUT at stop_price
  6. **fill_model: no trigger** — bar within range → None
  7. **BacktestEngine regression** — Run a known backtest scenario, verify identical results pre/post refactor (capture expected results in test fixture)
  8. **tracker: position opens with correct fields** — track() returns position_id, position has correct entry/stop/target/rejection data
  9. **tracker: candle processing closes at stop** — open position, feed candle with low < stop → position closed as STOPPED_OUT
  10. **tracker: candle processing closes at target** — feed candle with high > target → TARGET_HIT
  11. **tracker: MAE/MFE tracking** — feed multiple candles, verify max adverse/favorable excursion updated
  12. **tracker: backfill from IntradayCandleStore** — mock candle store with bars that breach stop → position immediately closed on open
  13. **tracker: backfill no bars** — candle store has no bars → position opens normally, forward monitoring only
  14. **tracker: empty target_prices** — signal with empty tuple → track() skips, logs warning
- Minimum new test count: 12
- Test file: `tests/intelligence/test_counterfactual.py` and `tests/core/test_fill_model.py`
- Test command: `python -m pytest tests/intelligence/test_counterfactual.py tests/core/test_fill_model.py -x -q`

## Definition of Done
- [ ] `argus/core/fill_model.py` created with `ExitReason`, `ExitResult`, `evaluate_bar_exit()`
- [ ] `argus/backtest/engine.py` refactored to call `evaluate_bar_exit()` — behavior preserved
- [ ] `argus/intelligence/counterfactual.py` created with `RejectionStage`, `CounterfactualPosition`, `CounterfactualTracker`
- [ ] IntradayCandleStore backfill implemented in `track()` method
- [ ] All existing tests pass
- [ ] ≥12 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| BacktestEngine produces identical results after fill model extraction | Run `python -m pytest tests/backtest/ -x -q` — all existing backtest tests pass with same results |
| `evaluate_bar_exit()` matches original priority: stop > target > time_stop > EOD | Unit tests for each priority case, including same-bar stop+target |
| No new imports or changes in `argus/core/events.py` | `git diff argus/core/events.py` shows no changes |
| No changes to strategy files | `git diff argus/strategies/` shows only no changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-27.7/session-1-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.7/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.7/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/intelligence/test_counterfactual.py tests/core/test_fill_model.py tests/backtest/ -x -q`
5. Files that should NOT have been modified: `argus/core/events.py`, `argus/main.py`, `argus/core/risk_manager.py`, `argus/core/regime.py`, `argus/data/intraday_candle_store.py`, any files in `argus/strategies/`, any files in `argus/ui/`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-27.7/session-1-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the post-review fix
documentation protocol (see implementation prompt template for full instructions).

## Session-Specific Review Focus (for @reviewer)
1. Verify `evaluate_bar_exit()` fill priority exactly matches BacktestEngine's original logic — compare line-by-line if needed
2. Verify the BacktestEngine refactor is behavior-preserving — no new edge cases introduced, no priority changes
3. Verify CounterfactualTracker uses T1 only from `signal.target_prices` tuple
4. Verify IntradayCandleStore backfill processes bars through the same `evaluate_bar_exit()` function (not a separate implementation)
5. Verify MAE/MFE tracking logic is correct for LONG positions (MAE = max of entry-low, MFE = max of high-entry)
6. Verify empty `target_prices` guard exists and logs warning

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] All existing pytest tests pass (~3,412 ± tolerance)
- [ ] All existing Vitest tests pass (~633)
- [ ] BacktestEngine produces identical results after fill model extraction
- [ ] `evaluate_bar_exit()` matches original fill priority for all edge cases
- [ ] Do-not-modify files are untouched

## Sprint-Level Escalation Criteria (for @reviewer)
- BacktestEngine regression after fill model extraction → HALT
- Fill priority disagreement → HALT
- Any pre-existing test failure → HALT
