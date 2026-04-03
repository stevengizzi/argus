# Sprint 31A, Session 2: PMH 0-Trade Fix

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC, PatternParam, CandleBar)
   - `argus/strategies/pattern_strategy.py` (focus on `on_candle()` lines ~244–340, `_try_backfill_from_store()`, `_get_candle_window()`, `backfill_candles()`, `initialize_reference_data()`)
   - `argus/strategies/patterns/premarket_high_break.py` (full file — `lookback_bars`, `set_reference_data()`, `detect()`)
   - `argus/strategies/patterns/gap_and_go.py` (focus on `set_reference_data()` and `lookback_bars`)
   - `argus/main.py` (focus on Phase 9.5 UM routing + watchlist population, lines ~920–960; R2G `initialize_prior_closes()` wiring)
   - `argus/data/universe_manager.py` (focus on `get_reference_data()`, `_reference_cache`)
2. Run the test baseline (DEC-328):
   Scoped: `python -m pytest tests/strategies/ -x -q -n auto`
   Expected: all passing
3. Verify you are on the correct branch: `main` (with S1 changes committed)

## Objective
Fix the Pre-Market High Break 0-trade root cause by adding `min_detection_bars` to PatternModule ABC, increasing PMH lookback to hold the full PM session, and wiring reference data (prior_closes) for PMH and GapAndGo.

## Root Cause Analysis
PMH generated 0 live trades because:
1. **lookback_bars=30** limits the PatternBasedStrategy deque to 30 candles. By 9:55 AM, zero pre-market candles remain in the deque → detection impossible. In backtest, the full day's candles are provided.
2. **Backfill truncation:** `backfill_candles()` takes `combined[-max_len:]` — only the last 30 of the store's ~330 PM bars.
3. **Missing reference data:** `initialize_reference_data()` is never called for PatternBasedStrategy patterns in main.py. PMH and GapAndGo never receive prior_closes.

## Requirements

### 1. Add `min_detection_bars` to PatternModule ABC

In `argus/strategies/patterns/base.py`, add a new property to the `PatternModule` class:

```python
@property
def min_detection_bars(self) -> int:
    """Minimum candle count before detection is attempted.

    Defaults to lookback_bars for backward compatibility. Override in
    patterns that need a large deque (for historical context) but can
    begin detection with fewer bars.

    PatternBasedStrategy uses lookback_bars for deque maxlen (storage
    capacity) and min_detection_bars for the detection-eligibility check.
    """
    return self.lookback_bars
```

This is NOT abstract — it has a default implementation that preserves existing behavior.

### 2. Update PatternBasedStrategy detection threshold

In `argus/strategies/pattern_strategy.py`, in the `on_candle()` method, change the detection-eligibility check from:

```python
lookback = self._pattern.lookback_bars
```
to:
```python
lookback = self._pattern.min_detection_bars
```

This affects the `bar_count < lookback` check (~line 293) and the partial-history threshold computation. The deque `maxlen` in `_get_candle_window()` continues to use `self._pattern.lookback_bars` (unchanged — this controls storage capacity).

### 3. Increase PMH lookback and set min_detection_bars

In `argus/strategies/patterns/premarket_high_break.py`:

Change `lookback_bars` property from `return 30` to `return 400`.

Add a `min_detection_bars` property:
```python
@property
def min_detection_bars(self) -> int:
    """PMH needs large deque for full PM session but can detect with few bars."""
    return 10
```

**Rationale:** 400 bars covers 4:00 AM to ~10:40 AM (the full PM session + first hour of market). `min_detection_bars=10` allows detection as soon as there are a few PM candles + a few market candles. The pattern's own `min_pm_candles` check (default 3) provides the real minimum PM bar requirement.

### 4. Wire reference data for PMH and GapAndGo in main.py

In `argus/main.py`, after the UM routing phase populates strategy watchlists (Phase 9.5, near the R2G `initialize_prior_closes()` block around line ~932):

Add reference data initialization for PatternBasedStrategy patterns that use `set_reference_data()`:

```python
# Initialize reference data for patterns that need prior_closes (PMH, GapAndGo)
# Similar to R2G initialize_prior_closes() above (Sprint 27.65 S3)
if universe_manager is not None and universe_manager.is_ready:
    prior_closes: dict[str, float] = {}
    for sym in universe_manager.viable_symbols:
        ref = universe_manager.get_reference_data(sym)
        if ref is not None and hasattr(ref, 'last_close') and ref.last_close:
            prior_closes[sym] = ref.last_close

    if prior_closes:
        # Wire to strategies that implement set_reference_data()
        for strategy in strategies:
            if isinstance(strategy, PatternBasedStrategy):
                strategy.initialize_reference_data({"prior_closes": prior_closes})
```

**Important:** Check what attribute on `SymbolReferenceData` holds the prior close. It might be `last_close`, `close`, or `price`. Inspect the model definition in `argus/data/fmp_reference.py` or `argus/models/` to find the correct field name.

Also add the same wiring in the periodic watchlist refresh block (~line 1448) where R2G re-initializes.

### 5. Verify backfill interaction

With `lookback_bars=400`, the deque holds 400 bars. `_try_backfill_from_store()` calls `store.get_bars(symbol)` which returns up to 720 bars. `backfill_candles()` takes `combined[-400:]` — the most recent 400. At 9:35 AM, that's ~335 PM bars + 5 market bars = 340. At 10:30 AM (latest entry), that's ~335 PM + 60 market = 395. This works correctly.

No changes needed to backfill logic — the increased maxlen naturally accommodates the full PM session.

## Constraints
- Do NOT modify any pattern file other than `premarket_high_break.py`
- Do NOT modify `pattern_strategy.py` beyond the `min_detection_bars` threshold change (do not touch backfill logic, candle accumulation, operating window check, or signal generation)
- Do NOT modify `base.py` beyond adding the `min_detection_bars` property
- Do NOT modify `gap_and_go.py` (it already has `set_reference_data()` — it just needs main.py to call `initialize_reference_data()`)
- Do NOT change `_get_candle_window()` deque maxlen source — it must remain `self._pattern.lookback_bars`
- Do NOT add any API routes or frontend changes
- R2G's existing `initialize_prior_closes()` wiring must remain unchanged and functional

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. Test that `PatternModule.min_detection_bars` defaults to `lookback_bars` for a pattern that doesn't override it (e.g., BullFlagPattern)
  2. Test that PMH `lookback_bars` is 400 and `min_detection_bars` is 10
  3. Test that PatternBasedStrategy with PMH pattern starts detection after 10 bars (not 400)
  4. Test that PatternBasedStrategy with BullFlagPattern still starts detection at `lookback_bars` (backward compat)
  5. Test PMH detect() with 300 PM candles + 10 market candles — should find PM high from full PM set
  6. Test PMH `_resolve_prior_close()` returns correct value when prior_closes is populated via `set_reference_data()`
  7. Test that `initialize_reference_data()` on PatternBasedStrategy forwards to pattern's `set_reference_data()`
  8. Test reference data wiring is skipped gracefully when UM is None/not ready (no crash)
- Minimum new test count: 8
- Test command: `python -m pytest tests/strategies/ -x -q -n auto`

## Definition of Done
- [ ] `min_detection_bars` property added to PatternModule (non-abstract, defaults to lookback_bars)
- [ ] PatternBasedStrategy uses `min_detection_bars` for detection eligibility
- [ ] PMH lookback_bars=400, min_detection_bars=10
- [ ] Existing patterns unchanged (min_detection_bars == lookback_bars)
- [ ] Reference data wired for PatternBasedStrategy patterns in main.py
- [ ] R2G wiring unchanged
- [ ] All existing tests pass
- [ ] ≥8 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| BullFlag detection unchanged | Test: BullFlagPattern().min_detection_bars == BullFlagPattern().lookback_bars |
| PMH deque holds PM data | PMH lookback_bars == 400 |
| PMH fires early | PMH min_detection_bars == 10 |
| R2G wiring intact | Grep main.py for `initialize_prior_closes` — still present and unchanged |
| No pattern file changes | `git diff argus/strategies/patterns/ -- ':!premarket_high_break.py' ':!base.py'` shows nothing |

## Sprint-Level Escalation Criteria
1. min_detection_bars changes existing pattern behavior → STOP, escalate
2. Test count decreases → STOP, investigate
3. DEF-143 fix breaks backtest results → STOP (may surface in this session's tests)

## Close-Out
Write the close-out report to: `docs/sprints/sprint-31a/session-2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context file: `docs/sprints/sprint-31a/review-context.md`
2. Close-out report: `docs/sprints/sprint-31a/session-2-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/strategies/ -x -q -n auto`
5. Files NOT modified: any pattern file except premarket_high_break.py and base.py, orchestrator.py, risk_manager.py, engine.py, any frontend file

## Session-Specific Review Focus (for @reviewer)
1. Verify `min_detection_bars` defaults to `lookback_bars` (not hardcoded, uses property delegation)
2. Verify `_get_candle_window()` still uses `lookback_bars` for maxlen — NOT min_detection_bars
3. Verify PMH lookback=400 is sufficient (4 AM to 10:40+ AM = ~400 bars)
4. Verify reference data wiring uses correct SymbolReferenceData field for last close price
5. Verify reference data re-wires on periodic watchlist refresh (not just startup)
6. Verify no import cycles introduced by main.py referencing PatternBasedStrategy
