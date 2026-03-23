---BEGIN-CLOSE-OUT---

**Session:** Sprint 21.6 — Session 3: Re-Validation Harness Script
**Date:** 2026-03-23
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `scripts/revalidate_strategy.py` | added | CLI script for BacktestEngine-based fixed-parameter walk-forward validation |
| `tests/backtest/test_revalidation_harness.py` | added | Unit tests for config extraction, baseline parsing, and divergence detection |

### Judgment Calls
- **ORB `min_gap_pct` default:** YAML config doesn't have a `min_gap_pct` field (it's a scanner param). Used default 2.0 (matching scanner default) when not present in YAML.
- **ORB `stop_buffer_pct` default:** Not in strategy YAML. Defaulted to 0.0 (no buffer), matching the most common VectorBT sweep baseline.
- **ORB Scalp `max_hold_bars` conversion:** YAML has `max_hold_seconds=120`; divided by 60 for 1-minute bars → 2 bars. Used `max(1, ...)` to prevent zero.
- **BacktestEngine fallback for red_to_green:** `evaluate_fixed_params_on_is()` only dispatches orb, orb_scalp, vwap_reclaim, and afternoon_momentum. Red-to-green falls through to the ORB handler (incorrect). Classified as needing BacktestEngine-only fallback alongside bull_flag and flat_top_breakout.
- **BacktestResult `total_pnl`:** `BacktestResult` dataclass doesn't have a `total_pnl` field. Computed as `final_equity - initial_capital`.
- **Bull Flag / Flat-Top param extraction:** Used a generic approach — extract all scalar YAML keys that aren't in the metadata skip-set (strategy_id, name, version, etc.), since PatternModule strategies have variable param schemas.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| CLI script with all required args | DONE | `scripts/revalidate_strategy.py:parse_args()` |
| Supports all 7 strategy types | DONE | `_WALK_FORWARD_SUPPORTED` (4) + BacktestEngine fallback (3) |
| Load strategy config from YAML | DONE | `extract_fixed_params()` uses `load_yaml_file()` |
| Build fixed params per strategy | DONE | `extract_fixed_params()` with 7 strategy-specific mappings |
| Run walk-forward (supported strategies) | DONE | `run_validation()` → `run_fixed_params_walk_forward()` |
| BacktestEngine fallback (unsupported) | DONE | `run_backtest_engine_fallback()` for r2g, bull_flag, flat_top |
| Compare against YAML baseline | DONE | `detect_divergence()` with configurable thresholds |
| Output structured JSON | DONE | JSON schema matches spec (strategy, baseline, new_results, divergence, status) |
| Divergence detection (Sharpe > 0.5) | DONE | `SHARPE_DIVERGENCE_THRESHOLD = 0.5` |
| Print summary to stdout | DONE | `print_summary()` |
| 6 new tests (min 5) | DONE | 19 tests in `test_revalidation_harness.py` |
| No source files modified | DONE | Only new files in `scripts/` and `tests/` |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| No source files modified | PASS | `git diff --name-only` empty |
| Walk-forward module unchanged | PASS | No changes to `argus/backtest/walk_forward.py` |
| Script is independently runnable | PASS | `python scripts/revalidate_strategy.py --help` prints usage |
| Config loading uses load_yaml_file | PASS | `from argus.core.config import load_yaml_file` in script |
| All existing tests still pass | PASS | 3,041 passed (full suite with xdist) |

### Test Results
- Tests run: 3,041 (full suite) + 19 (new tests specifically)
- Tests passed: 3,041
- Tests failed: 0
- New tests added: 19
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q` and `python -m pytest tests/backtest/test_revalidation_harness.py -x -q`

### Unfinished Work
None

### Notes for Reviewer
- Verify the YAML → fixed-params mappings against walk_forward.py CLI arg sections (lines 2582–2619) for orb, orb_scalp, vwap_reclaim.
- Afternoon momentum param names match `_evaluate_fixed_params_afternoon_momentum()` (line 1906–1917).
- Red-to-green, bull_flag, flat_top_breakout use BacktestEngine-only fallback because `evaluate_fixed_params_on_is()` would incorrectly fall through to the ORB VectorBT path.
- The script is a standalone CLI tool — it does NOT modify walk_forward.py or engine.py.
- Context State: GREEN

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "21.6",
  "session": "S3",
  "verdict": "COMPLETE",
  "tests": {
    "before": 3022,
    "after": 3041,
    "new": 19,
    "all_pass": true
  },
  "files_created": [
    "scripts/revalidate_strategy.py",
    "tests/backtest/test_revalidation_harness.py"
  ],
  "files_modified": [],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "evaluate_fixed_params_on_is() in walk_forward.py does not have a red_to_green dispatch path — it falls through to ORB. If a full WFE re-validation for R2G is needed in the future, walk_forward.py would need a red_to_green branch.",
    "BacktestResult has no total_pnl field; computed as final_equity - initial_capital. May want to add a property for consistency."
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Script uses BacktestEngine-only fallback for 3 strategies (red_to_green, bull_flag, flat_top_breakout) that lack VectorBT IS evaluation paths. These produce single-run metrics without WFE. The 4 supported strategies (orb, orb_scalp, vwap_reclaim, afternoon_momentum) get full windowed walk-forward with WFE computation."
}
```
