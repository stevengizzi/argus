---BEGIN-CLOSE-OUT---

**Session:** Sprint 21.6.1 — BacktestEngine Position Sizing + Data Compatibility
**Date:** 2026-03-23
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/backtest/engine.py | modified | Fix 1: Legacy position sizing for share_count=0 signals in _on_candle_event(); Fix 3: Auto-detect symbols from cache dir in _load_data() |
| argus/backtest/walk_forward.py | modified | Fix 3: Propagate detected symbols to BacktestEngine OOS path; added `replace` to dataclasses import |
| argus/backtest/vectorbt_orb.py | modified | Fix 2: Dual naming convention fallback for load_symbol_data() |
| argus/backtest/vectorbt_orb_scalp.py | modified | Fix 2: Dual naming convention fallback for load_symbol_data() |
| argus/backtest/vectorbt_vwap_reclaim.py | modified | Fix 2: Dual naming convention fallback for load_symbol_data() |
| argus/backtest/vectorbt_afternoon_momentum.py | modified | Fix 2: Dual naming convention fallback for load_symbol_data() |
| argus/backtest/vectorbt_red_to_green.py | modified | Fix 2: Dual naming convention fallback for load_symbol_data() |
| tests/backtest/test_engine_sizing.py | added | 4 tests: position sizing, zero risk, nonzero preservation, symbol auto-detect |
| tests/backtest/test_vectorbt_data_loading.py | added | 2 tests: legacy naming, Databento naming |

### Judgment Calls
None — all decisions were pre-specified in the implementation prompt.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| BacktestEngine _on_candle_event() legacy sizing for share_count=0 | DONE | engine.py:_on_candle_event() — getattr chain with 0.01 default, dataclasses.replace() |
| All 5 VectorBT load_symbol_data() accept both naming conventions | DONE | vectorbt_orb.py, vectorbt_orb_scalp.py, vectorbt_vwap_reclaim.py, vectorbt_afternoon_momentum.py, vectorbt_red_to_green.py |
| BacktestEngine _load_data() auto-detects symbols from cache | DONE | engine.py:_load_data() — iterdir() with hidden dir filter |
| Walk-forward OOS path propagates detected symbols | DONE | walk_forward.py:_validate_oos() — dataclasses.replace() for config copy |
| 6+ new tests passing | DONE | 4 in test_engine_sizing.py + 2 in test_vectorbt_data_loading.py |
| All existing tests still pass | DONE | 383 passed (377 baseline + 6 new) |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Existing backtest tests pass | PASS | 377 original tests pass |
| BacktestEngine works with explicit symbols | PASS | Existing test_engine.py tests use explicit symbols |
| VectorBT still loads legacy-named files | PASS | test_load_symbol_data_legacy_naming |
| No changes to strategy files | PASS | No argus/strategies/ files in diff |
| No changes to execution/core files | PASS | No argus/core/ or argus/execution/ files in diff |
| `replace` import available | PASS | Module-level import in engine.py |
| Position sizing only triggers for share_count=0 | PASS | test_on_candle_event_preserves_nonzero_shares |

### Test Results
- Tests run: 383
- Tests passed: 383
- Tests failed: 0
- New tests added: 6
- Command used: `python -m pytest tests/backtest/ -x -q`

### Unfinished Work
None — all spec items are complete.

### Notes for Reviewer
- Position sizing formula matches main.py:_process_signal() bypass path exactly: `allocated_capital * max_loss_per_trade_pct / risk_per_share`
- The `getattr` chain handles PatternBasedStrategy and any non-standard config shapes by defaulting to 0.01 (1%)
- All 5 VectorBT glob changes are identical — legacy pattern first, then fallback to `*.parquet`
- Walk-forward symbol propagation uses `dataclasses.replace()` since WalkForwardConfig is a dataclass

### Post-Review Notes
- **Reviewer CONCERN (false positive):** Reviewer flagged `config/system_live.yaml` as undocumented scope creep. This is a pre-existing uncommitted change in the working tree — it is NOT part of this session's commit (verified via `git show HEAD --name-only`). The reviewer's `git diff HEAD~1` picked up the unstaged working tree change. Self-assessment CLEAN stands.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "21.6.1",
  "session": "S1",
  "verdict": "COMPLETE",
  "tests": {
    "before": 377,
    "after": 383,
    "new": 6,
    "all_pass": true
  },
  "files_created": [
    "tests/backtest/test_engine_sizing.py",
    "tests/backtest/test_vectorbt_data_loading.py"
  ],
  "files_modified": [
    "argus/backtest/engine.py",
    "argus/backtest/walk_forward.py",
    "argus/backtest/vectorbt_orb.py",
    "argus/backtest/vectorbt_orb_scalp.py",
    "argus/backtest/vectorbt_vwap_reclaim.py",
    "argus/backtest/vectorbt_afternoon_momentum.py",
    "argus/backtest/vectorbt_red_to_green.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Three related bugs causing BacktestEngine zero-trade output. Fix 1 adds legacy position sizing (matching main.py bypass path) so Risk Manager receives nonzero share_count. Fix 2 adds Databento naming fallback to all 5 VectorBT load_symbol_data() functions. Fix 3 adds symbol auto-detection from cache directory in both engine.py and walk_forward.py."
}
```
