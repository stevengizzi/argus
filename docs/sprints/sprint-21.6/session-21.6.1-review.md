---BEGIN-REVIEW---

# Tier 2 Review: Sprint 21.6.1, Session 1

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-23
**Commit reviewed:** HEAD (52940e2 parent, diff via `git diff HEAD~1`)

## Summary

Session implements three related fixes for BacktestEngine zero-trade output: legacy position sizing for `share_count=0` signals, dual VectorBT file naming convention support, and symbol auto-detection from cache directories. Six new tests added, all 383 backtest tests pass.

## Review Focus Findings

### 1. Position sizing formula match

**PASS.** The BacktestEngine formula in `engine.py` line 297 uses:
```
allocated_capital * max_loss_pct / risk_per_share
```
This matches `main.py:_process_signal()` lines 954-958:
```
strategy.allocated_capital * strategy.config.risk_limits.max_loss_per_trade_pct / risk_per_share
```
Both compute `risk_per_share = abs(entry_price - stop_price)` and use `int()` truncation. Minor difference: BacktestEngine adds `max(shares, 0)` which is redundant (all inputs are non-negative due to `abs()`) but harmless.

### 2. getattr chain safety

**PASS.** The triple-nested `getattr` chain defaults each level to `None`, with the final `max_loss_per_trade_pct` defaulting to `0.01`. This handles: (a) strategies without a `config` attribute, (b) configs without `risk_limits`, (c) risk_limits without `max_loss_per_trade_pct`. PatternBasedStrategy and other non-standard shapes will safely fall through to the 0.01 default.

### 3. share_count == 0 guard

**PASS.** The sizing block is gated by `if signal.share_count == 0:` at line 19 of the diff. Signals with nonzero shares skip the block entirely. Verified by `test_on_candle_event_preserves_nonzero_shares` which asserts share_count=50 passes through untouched.

### 4. VectorBT glob changes consistency

**PASS.** All five files have identical three-line additions:
```python
# Support both naming conventions:
# - Legacy: {SYMBOL}_{YYYY-MM}.parquet (Alpaca-era data_fetcher)
# - Current: {YYYY-MM}.parquet (HistoricalDataFeed / Databento cache)
parquet_files = sorted(symbol_dir.glob(f"{symbol.upper()}_*.parquet"))
if not parquet_files:
    parquet_files = sorted(symbol_dir.glob("*.parquet"))
```
No copy-paste errors. All five comments and code lines are character-identical.

### 5. Auto-detect hidden directory filtering

**PASS.** Both `engine.py` and `walk_forward.py` use `not d.name.startswith(".")` to skip hidden directories, and `d.is_dir()` to skip non-directory entries. Test `test_load_data_auto_detects_symbols` explicitly creates a `.hidden` directory and asserts it is excluded.

### 6. Boundary check (files outside scope)

**CONCERN.** The diff includes a modification to `config/system_live.yaml` (line 154: `reference_cache_ttl_hours: 24` changed to `72`). This change:
- Is not mentioned in the close-out report change manifest
- Is not part of the sprint spec
- Is outside the declared scope boundary (`argus/backtest/` only)
- Was not listed in the "files that should NOT have been modified" boundary list (which only covered source code directories, not config/)

The change itself is low-risk (extends FMP reference data cache from 24h to 72h), but it is undocumented scope creep. The close-out self-assessment of CLEAN is inaccurate given this undeclared modification.

## Additional Observations

- The `replace` import is at module level in `engine.py` (line 9 of diff), which is cleaner than the inline import suggested in the spec. Good judgment call.
- Walk-forward uses `dataclasses.replace()` correctly for the `WalkForwardConfig` dataclass copy (not Pydantic `.model_copy()`). The `replace` import was added to the existing `dataclasses` import line.
- Tests are well-structured with descriptive names following project conventions.
- The `docs/sprints/sprint-21.6/sprint-21.6.1-session-1-impl.md` implementation prompt is included in the commit, which is acceptable for documentation purposes.

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| replace() doesn't work with SignalEvent | No -- SignalEvent is a dataclass, replace() works correctly |
| Position sizing introduces circular import | No -- only uses `dataclasses.replace`, no new imports |
| Existing backtest tests break | No -- all 377 pre-existing tests pass |

## Test Verification

- Command: `python -m pytest tests/backtest/ -x -q`
- Result: 383 passed, 0 failed (20.81s)
- New tests: 6 (4 in test_engine_sizing.py, 2 in test_vectorbt_data_loading.py)
- Delta: +6 from baseline (377 -> 383), matches close-out report

## Verdict

**CONCERNS**

The implementation is functionally correct and all spec requirements are met. The single concern is the undocumented `config/system_live.yaml` change (`reference_cache_ttl_hours: 24 -> 72`) which violates scope discipline (RULE-007) and makes the CLEAN self-assessment inaccurate. This is a low-severity finding -- the config change is non-destructive and does not affect backtest behavior -- but it should be documented.

**Recommended action:** Add the `config/system_live.yaml` change to the close-out report change manifest, or revert it if it was unintentional.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "21.6.1",
  "session": "S1",
  "verdict": "CONCERNS",
  "findings": [
    {
      "severity": "low",
      "category": "scope-creep",
      "description": "config/system_live.yaml modified (reference_cache_ttl_hours 24->72) without documentation in close-out report or sprint spec. Undeclared out-of-scope change.",
      "file": "config/system_live.yaml",
      "line": 154,
      "recommendation": "Document in close-out report or revert if unintentional"
    }
  ],
  "tests_pass": true,
  "test_count": 383,
  "boundary_violations": [
    "config/system_live.yaml modified but not in declared scope"
  ],
  "escalation_triggers_fired": [],
  "close_out_accurate": false,
  "close_out_discrepancies": [
    "config/system_live.yaml change not listed in change manifest",
    "Self-assessment CLEAN but undeclared file modification present"
  ]
}
```
