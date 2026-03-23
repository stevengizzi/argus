# Sprint 21.6.1, Session 1: BacktestEngine Position Sizing + Data Compatibility

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/engine.py` lines 279–291 — `_on_candle_event()` signal flow (the bug)
   - `argus/backtest/engine.py` lines 295–331 — `_load_data()` symbols handling
   - `argus/main.py` lines 931–960 — `_process_signal()` legacy bypass path (the reference implementation)
   - `argus/backtest/walk_forward.py` lines 547–555 — VectorBT symbol auto-detect pattern
   - `argus/backtest/walk_forward.py` lines 751–808 — `_validate_oos_backtest_engine()` (symbols=None issue)
   - `argus/backtest/vectorbt_orb.py` lines 138–155 — `load_symbol_data()` glob pattern (naming mismatch)
   - `argus/strategies/base.py` — BaseStrategy.allocated_capital, config.risk_limits
2. Run scoped test baseline (DEC-328):
   ```
   python -m pytest tests/backtest/ -x -q
   ```
   Expected: all passing
3. Verify you are on branch: `main`

## Objective
Fix three related bugs discovered during Sprint 21.6 re-validation that cause BacktestEngine to produce zero trades for all strategies:
1. **Position sizing gap** — BacktestEngine passes signals with `share_count=0` directly to Risk Manager, which rejects them at Check 0. Since Sprint 24, all strategies emit `share_count=0` expecting the quality pipeline to size them.
2. **VectorBT file naming mismatch** — VectorBT `load_symbol_data()` globs `{SYMBOL}_*.parquet` but `HistoricalDataFeed` writes `{YYYY-MM}.parquet`.
3. **BacktestEngine symbols=None** — `_load_data()` treats `symbols=None` as empty list and returns no data. Walk-forward OOS path passes `config.symbols` (which may be None) without auto-detecting.

## Requirements

### Fix 1: BacktestEngine Position Sizing (CRITICAL)

In `argus/backtest/engine.py`, modify `_on_candle_event()` (line 279). After getting a signal from the strategy, add legacy position sizing before passing to Risk Manager. Model after `main.py:_process_signal()` bypass path (lines 949–960):

```python
async def _on_candle_event(self, event: CandleEvent) -> None:
    if self._strategy is None:
        return

    signal = await self._strategy.on_candle(event)
    if signal is not None and self._risk_manager is not None:
        # Legacy position sizing for backtest mode (Sprint 24 quality pipeline
        # is not wired into BacktestEngine — strategies emit share_count=0)
        if signal.share_count == 0:
            risk_per_share = abs(signal.entry_price - signal.stop_price)
            if risk_per_share > 0:
                from dataclasses import replace
                max_loss_pct = getattr(
                    getattr(getattr(self._strategy, 'config', None), 'risk_limits', None),
                    'max_loss_per_trade_pct', 0.01
                )
                shares = int(
                    self._strategy.allocated_capital * max_loss_pct / risk_per_share
                )
                signal = replace(signal, share_count=max(shares, 0))
            # If risk_per_share == 0 or shares == 0, let Risk Manager reject it

        result = await self._risk_manager.evaluate_signal(signal)
        await self._event_bus.publish(result)
```

**Key requirements:**
- Import `replace` from `dataclasses` (at module level or inline — your choice, but module level is cleaner)
- Use `getattr` chain with safe defaults — BacktestEngine creates strategies via its own factory, and the config structure may vary (e.g., PatternBasedStrategy wraps PatternModule)
- Default `max_loss_per_trade_pct` to `0.01` (1%) if the attribute chain fails — matches the most common strategy config value
- Never modify the original signal object (it's frozen) — use `replace()`
- Do NOT wire the full quality pipeline (SetupQualityEngine, DynamicPositionSizer) into BacktestEngine — legacy sizing is correct for backtesting

### Fix 2: VectorBT File Naming Compatibility

In all 5 VectorBT backtest files, change the `load_symbol_data()` glob pattern to accept both naming conventions:

**Files to modify:**
- `argus/backtest/vectorbt_orb.py` (line 144)
- `argus/backtest/vectorbt_orb_scalp.py` (line 136)
- `argus/backtest/vectorbt_vwap_reclaim.py` (line 150)
- `argus/backtest/vectorbt_afternoon_momentum.py` (line 163)
- `argus/backtest/vectorbt_red_to_green.py` (line 158)

In each file, change:
```python
parquet_files = sorted(symbol_dir.glob(f"{symbol.upper()}_*.parquet"))
```
to:
```python
# Support both naming conventions:
# - Legacy: {SYMBOL}_{YYYY-MM}.parquet (Alpaca-era data_fetcher)
# - Current: {YYYY-MM}.parquet (HistoricalDataFeed / Databento cache)
parquet_files = sorted(symbol_dir.glob(f"{symbol.upper()}_*.parquet"))
if not parquet_files:
    parquet_files = sorted(symbol_dir.glob("*.parquet"))
```

This preserves backward compatibility (legacy files match first) while falling back to the HistoricalDataFeed naming convention.

### Fix 3: BacktestEngine Symbols Auto-Detection

In `argus/backtest/engine.py`, modify `_load_data()` (line 295). When `symbols` is None or empty, auto-detect from cache directory (same pattern as walk_forward.py lines 547–555):

```python
async def _load_data(self) -> None:
    symbols = self._config.symbols or []
    if not symbols:
        # Auto-detect symbols from cache directory
        cache_path = Path(self._config.cache_dir)
        if cache_path.is_dir():
            symbols = [
                d.name for d in cache_path.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
        if not symbols:
            logger.warning(
                "No symbols configured and none found in cache — backtest will have no data"
            )
            return
        logger.info("Auto-detected %d symbols from cache: %s", len(symbols), symbols[:5])

    # ... rest of method unchanged
```

Also, in `argus/backtest/walk_forward.py`, in the `_validate_oos` function near line 722, ensure detected symbols propagate to the BacktestEngine OOS call. Find where `_validate_oos_backtest_engine` is called and verify `config.symbols` is not None at that point. If it can be None, add symbol detection before the call:

```python
if config.oos_engine == "backtest_engine":
    # Ensure symbols are explicit for BacktestEngine (it needs them for _load_data)
    oos_config = config
    if not config.symbols:
        detected = [
            d.name for d in Path(config.data_dir).iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        oos_config = config.__class__(**{**config.__dict__, 'symbols': detected})
    return await _validate_oos_backtest_engine(
        oos_start, oos_end, best_params, oos_config
    )
```

**Note:** Check whether `WalkForwardConfig` is a dataclass or Pydantic model and use the appropriate copy method (`replace()` for dataclass, `.model_copy(update=...)` for Pydantic).

## Constraints
- Do NOT modify: any file in `argus/strategies/`, `argus/core/`, `argus/ui/`, `argus/api/`, `argus/execution/`, `argus/intelligence/`
- Do NOT modify: `argus/backtest/historical_data_feed.py`, `argus/backtest/config.py`
- Do NOT wire: SetupQualityEngine or DynamicPositionSizer into BacktestEngine — use legacy sizing only
- Do NOT change: Risk Manager behavior, Event Bus dispatch, strategy interfaces
- Do NOT change: the Parquet file format or HistoricalDataFeed write path — only fix the read path in VectorBT

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/backtest/test_engine_sizing.py`:
  1. `test_on_candle_event_sizes_position` — create a minimal BacktestEngine with a mock strategy that emits `share_count=0`, verify the signal passed to Risk Manager has `share_count > 0`
  2. `test_on_candle_event_zero_risk_per_share` — signal where `entry_price == stop_price`, verify Risk Manager still gets the signal (with share_count=0, which RM rejects — that's correct behavior)
  3. `test_on_candle_event_preserves_nonzero_shares` — if strategy emits `share_count=50` (future case), verify BacktestEngine does NOT override it
  4. `test_load_data_auto_detects_symbols` — create a temp cache dir with symbol subdirs, verify `_load_data` finds them when `config.symbols=None`
- New tests in `tests/backtest/test_vectorbt_data_loading.py`:
  5. `test_load_symbol_data_legacy_naming` — create temp dir with `{SYMBOL}_2024-01.parquet`, verify load works
  6. `test_load_symbol_data_databento_naming` — create temp dir with `2024-01.parquet`, verify load works
- Minimum new test count: 6
- Test command: `python -m pytest tests/backtest/test_engine_sizing.py tests/backtest/test_vectorbt_data_loading.py -x -q`

## Definition of Done
- [ ] BacktestEngine `_on_candle_event()` computes legacy position sizing for `share_count=0` signals
- [ ] All 5 VectorBT `load_symbol_data()` functions accept both file naming conventions
- [ ] BacktestEngine `_load_data()` auto-detects symbols from cache when `config.symbols` is None
- [ ] Walk-forward OOS path propagates detected symbols to BacktestEngine
- [ ] 6+ new tests passing
- [ ] All existing tests still pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing backtest tests pass | `python -m pytest tests/backtest/ -x -q` |
| BacktestEngine still works with explicit symbols | Test with `config.symbols=["AAPL"]` — no regression |
| VectorBT still loads legacy-named files | `test_load_symbol_data_legacy_naming` |
| No changes to strategy files | `git diff --name-only` shows no `argus/strategies/` files |
| No changes to execution/core files | `git diff --name-only` shows no `argus/core/` or `argus/execution/` files |
| `replace` import available | `python -c "from dataclasses import replace"` |
| Position sizing only triggers for share_count=0 | `test_on_candle_event_preserves_nonzero_shares` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

**Write the close-out report to a file:**
`docs/sprints/sprint-21.6/session-21.6.1-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The close-out report path: `docs/sprints/sprint-21.6/session-21.6.1-closeout.md`
2. The diff range: `git diff HEAD~1`
3. The test command: `python -m pytest tests/backtest/ -x -q`
4. Files that should NOT have been modified: any file in `argus/strategies/`, `argus/core/`, `argus/execution/`, `argus/intelligence/`, `argus/ui/`, `argus/api/`, `argus/backtest/historical_data_feed.py`, `argus/backtest/config.py`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-21.6/session-21.6.1-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same session, update both the close-out and review report files per the Post-Review Fix Documentation protocol in the implementation prompt template.

## Session-Specific Review Focus (for @reviewer)
1. Verify position sizing uses the same formula as `main.py:_process_signal()` bypass path — `allocated_capital * max_loss_per_trade_pct / risk_per_share`
2. Verify the `getattr` chain for `max_loss_per_trade_pct` has a safe default (0.01) and doesn't crash for PatternBasedStrategy or other non-standard config shapes
3. Verify position sizing only triggers when `signal.share_count == 0` — signals with nonzero shares must pass through untouched
4. Verify all 5 VectorBT glob changes are identical (no copy-paste errors, no missing files)
5. Verify `_load_data` auto-detect skips hidden directories (`.` prefix) and non-directory entries
6. Verify no changes to files outside `argus/backtest/` (boundary check)

## Escalation Criteria
1. If the `replace()` approach doesn't work with SignalEvent (e.g., if it's not a dataclass) → ESCALATE
2. If position sizing introduces a circular import → ESCALATE
3. If existing backtest tests break due to the sizing change → ESCALATE (may indicate tests that relied on zero-trade behavior)