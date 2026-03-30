```markdown
---BEGIN-REVIEW---

**Reviewing:** [Sprint 28.5 S5] — BacktestEngine + CounterfactualTracker Alignment
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-30
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All spec requirements implemented. Only expected files modified. |
| Close-Out Accuracy | PASS | Change manifest matches diff. Judgment calls documented. Self-assessment CLEAN is justified. |
| Test Health | PASS | 3,955 tests pass (21 new). All assertions use specific numeric values. |
| Regression Checklist | PASS | Non-trail behavior verified, fill_model.py untouched, AMD-7 ordering confirmed. |
| Architectural Compliance | PASS | Clean separation via _BacktestPosition dataclass. No architectural violations. |
| Escalation Criteria | NONE_TRIGGERED | No escalation criteria met. |

### Findings

**F1 (INFO): Test file paths differ from spec**
The implementation spec listed test files under `tests/unit/backtest/` and `tests/unit/intelligence/`, but the actual files were placed at `tests/backtest/test_engine_exit_management.py` and `tests/intelligence/test_counterfactual_exit_management.py`. This matches the project's actual test directory structure (no `tests/unit/` prefix), so this is correct behavior despite the spec naming.

**F2 (INFO): BacktestEngine _sync_bt_position calls get_managed_positions per bar**
`_sync_bt_position` is called at the start of every `_check_bracket_orders` invocation and internally calls `self._order_manager.get_managed_positions()`. This is a dict lookup that happens once per symbol per bar. Additionally, `_compute_escalation_for_position` also calls `get_managed_positions()` again to look up `time_stop_seconds`. In production backtests with many symbols/bars this creates redundant lookups. Not a correctness issue; performance impact is negligible for typical backtest sizes.

**F3 (INFO): Escalation phase index update uses linear scan**
In both `engine.py` (Step 3, around line 900) and `counterfactual.py` (Step 3, around line 595), the escalation phase advancement loops through all phases on every bar. This is functionally correct (later phases override earlier ones), but could skip already-passed phases by starting from `escalation_phase_index + 1`. Negligible performance concern given typical 2-3 phases.

### Critical Review Focus Items

1. **AMD-7 bar-processing order (VERIFIED):** In both `engine.py` (`_check_bracket_orders`) and `counterfactual.py` (`_process_bar`), the implementation follows the correct three-step ordering: (1) read prior trail/escalation state to compute effective stop, (2) evaluate exit against current bar, (3) update high_watermark and recompute trail/escalation for next bar. The high_watermark update occurs only in Step 3 (after exit evaluation), confirming the stop used for exit evaluation never incorporates the current bar's high. Test #7 validates this with specific numeric values: prior trail $49.50 triggers exit, not the updated $51.00.

2. **fill_model.py NOT modified (VERIFIED):** `git diff HEAD~1 -- argus/core/fill_model.py` returns empty. No changes.

3. **Non-trail bit-identical (VERIFIED):** When exit_config is None or both trailing_stop and escalation are disabled, `compute_effective_stop` receives only None optionals and returns the original stop price unchanged. Tests #5 and #11 verify this explicitly. The `_process_bar` in counterfactual.py passes `effective_stop` (which equals `pos.stop_price` when no trail/escalation) to `evaluate_bar_exit`, matching pre-sprint behavior.

4. **CounterfactualTracker backfill bars update trail state (VERIFIED):** The backfill loop at lines 303-312 calls `_process_bar` sequentially for each backfill bar. Inside `_process_bar`, AMD-7 Step 3 updates `high_watermark` and recomputes `trail_stop_price`, which is then used as prior state for the next bar's Step 1. Tests #12 and #13 verify this, including the early-exit guard when trail triggers mid-backfill.

5. **ExitManagementConfig loaded correctly (VERIFIED):** BacktestEngine loads via `_load_exit_management_config` (reads `exit_management.yaml` + strategy YAML overrides) and passes to OrderManager constructor. CounterfactualTracker receives via `exit_configs` constructor dict and looks up per-signal strategy_id.

6. **Test assertions use specific numeric values (VERIFIED):** All 21 tests use exact numeric assertions (e.g., `== 49.50`, `== 52.0`, `== 50.0`) rather than approximate comparisons.

### Recommendation
Proceed to next session.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "28.5",
  "session": "S5",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "Test file paths differ from spec (tests/unit/ prefix vs tests/) — matches actual project structure, not a real issue.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "tests/backtest/test_engine_exit_management.py",
      "recommendation": "No action needed."
    },
    {
      "description": "_sync_bt_position and _compute_escalation_for_position both call get_managed_positions() per bar, creating redundant dict lookups.",
      "severity": "INFO",
      "category": "PERFORMANCE",
      "file": "argus/backtest/engine.py",
      "recommendation": "Minor optimization opportunity; no action needed for correctness."
    },
    {
      "description": "Escalation phase index update uses linear scan from index 0 on every bar rather than starting from current phase index.",
      "severity": "INFO",
      "category": "PERFORMANCE",
      "file": "argus/intelligence/counterfactual.py",
      "recommendation": "Negligible with typical 2-3 phases. No action needed."
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All 13+ required tests implemented (21 total). AMD-7 ordering verified in both engines. Non-trail regression verified. fill_model.py untouched.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/backtest/engine.py",
    "argus/intelligence/counterfactual.py",
    "argus/core/exit_math.py",
    "tests/backtest/test_engine_exit_management.py",
    "tests/intelligence/test_counterfactual_exit_management.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 3955,
    "new_tests_adequate": true,
    "test_quality_notes": "21 new tests cover all 13 spec scenarios. Tests use specific numeric assertions. AMD-7 test (#7) explicitly demonstrates the prior-state-vs-updated-state difference. Regression tests (#5, #11) verify non-trail behavior is unchanged."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "BacktestEngine non-trail bit-identical", "passed": true, "notes": "Tests #5 verify default config produces original stop"},
      {"check": "CounterfactualTracker non-trail identical", "passed": true, "notes": "Tests #11 verify no-config and disabled-config use original stop"},
      {"check": "fill_model.py not modified", "passed": true, "notes": "git diff confirms zero changes"},
      {"check": "AMD-7 ordering correct", "passed": true, "notes": "Step 1→2→3 ordering verified in both engines; Test #7 validates numerically"},
      {"check": "All existing backtest tests pass", "passed": true, "notes": "Full suite 3955 passed"},
      {"check": "All existing counterfactual tests pass", "passed": true, "notes": "Included in full suite"},
      {"check": "order_manager.py not modified", "passed": true, "notes": "git diff confirms zero changes"},
      {"check": "risk_manager.py not modified", "passed": true, "notes": "git diff confirms zero changes"},
      {"check": "No UI files modified", "passed": true, "notes": "git diff confirms zero changes"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": []
}
```
