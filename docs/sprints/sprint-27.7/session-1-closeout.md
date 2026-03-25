---BEGIN-CLOSE-OUT---

**Session:** Sprint 27.7 — Session 1: Core Model + Tracker Logic + Shared Fill Model
**Date:** 2026-03-25
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/core/fill_model.py | added | Shared TheoreticalFillModel: FillExitReason enum, ExitResult dataclass, evaluate_bar_exit() pure function |
| argus/backtest/engine.py | modified | Refactored _check_bracket_orders() and _check_time_stop() to use evaluate_bar_exit() from shared fill model |
| argus/intelligence/counterfactual.py | added | RejectionStage enum, CounterfactualPosition frozen dataclass, CounterfactualTracker class with IntradayCandleStore backfill |
| tests/core/test_fill_model.py | added | 10 tests covering all fill priority cases |
| tests/intelligence/test_counterfactual.py | added | 14 tests covering position open, candle processing, MAE/MFE, backfill, timeout, EOD close |

### Judgment Calls
- Named the fill model's exit reason enum `FillExitReason` (not `ExitReason`) to avoid collision with the existing `ExitReason` in `argus/core/events.py`. The spec said `ExitReason` but that name is already taken.
- BacktestEngine refactor: wrapped the `evaluate_bar_exit()` call in an `if stop_orders:` guard because the original code already had this guard (line 589: `if stop_orders and bar_low <= ...`). Without stop orders, using `float("inf")` as stop_price would incorrectly trigger stop on every bar since `bar_low <= inf` is always true.
- In `_check_time_stop`, passed `bar_high=float("-inf")` to `evaluate_bar_exit()` because the method doesn't have `bar_high` in its signature (target check already happened at Priority 2 in `_check_bracket_orders`). This ensures the target check in the shared model never triggers during the time stop path.
- `CounterfactualPosition` uses `dict[str, object]` for `regime_vector_snapshot` and `signal_metadata` types to match existing event conventions.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| 1a. FillExitReason enum (5 values) | DONE | argus/core/fill_model.py:FillExitReason |
| 1b. ExitResult frozen dataclass | DONE | argus/core/fill_model.py:ExitResult |
| 1c. evaluate_bar_exit() pure function | DONE | argus/core/fill_model.py:evaluate_bar_exit |
| 2a. BacktestEngine uses shared fill model | DONE | argus/backtest/engine.py:_check_bracket_orders + _check_time_stop |
| 2b. Behavior-preserving refactor | DONE | All 406 backtest tests pass unchanged |
| 3a. RejectionStage enum | DONE | argus/intelligence/counterfactual.py:RejectionStage |
| 3b. CounterfactualPosition frozen dataclass | DONE | argus/intelligence/counterfactual.py:CounterfactualPosition |
| 3c. CounterfactualTracker class | DONE | argus/intelligence/counterfactual.py:CounterfactualTracker |
| IntradayCandleStore backfill in track() | DONE | counterfactual.py:track() queries candle_store.get_bars() |
| ≥12 new tests | DONE | 24 new tests (10 fill model + 14 counterfactual) |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| BacktestEngine produces identical results after fill model extraction | PASS | 406 backtest tests pass |
| evaluate_bar_exit() matches original priority: stop > target > time_stop > EOD | PASS | 10 unit tests including same-bar stop+target |
| No new imports or changes in argus/core/events.py | PASS | git diff shows no changes |
| No changes to strategy files | PASS | git diff argus/strategies/ shows no changes |

### Test Results
- Tests run: 3,436
- Tests passed: 3,436
- Tests failed: 0
- New tests added: 24
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`

### Unfinished Work
None

### Notes for Reviewer
- The fill model enum is named `FillExitReason` (not `ExitReason`) to avoid collision with `argus.core.events.ExitReason`. Both enums serve different purposes: `ExitReason` is for real position exit reasons in the event system, `FillExitReason` is for the theoretical fill model.
- The BacktestEngine refactor is minimal — the `evaluate_bar_exit()` call replaces only the stop-vs-target priority decision. The multi-target iteration and broker interaction remain as-is.
- Verify the time stop edge case in `_check_time_stop`: `bar_high=float("-inf")` ensures the target check in the shared model never triggers (correct, since targets were already checked at Priority 2).

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27.7",
  "session": "S1",
  "verdict": "COMPLETE",
  "tests": {
    "before": 3412,
    "after": 3436,
    "new": 24,
    "all_pass": true
  },
  "files_created": [
    "argus/core/fill_model.py",
    "argus/intelligence/counterfactual.py",
    "tests/core/test_fill_model.py",
    "tests/intelligence/test_counterfactual.py"
  ],
  "files_modified": [
    "argus/backtest/engine.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Named fill model enum FillExitReason to avoid collision with existing ExitReason in events.py. BacktestEngine refactor is minimal — uses evaluate_bar_exit() for stop-vs-target priority decision only, keeping multi-target iteration and broker interaction unchanged."
}
```
