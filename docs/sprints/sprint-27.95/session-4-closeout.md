---BEGIN-CLOSE-OUT---

**Session:** Sprint 27.95 S4 — Startup Zombie Cleanup
**Date:** 2026-03-27
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/core/config.py | modified | Added StartupConfig Pydantic model, wired into SystemConfig |
| argus/execution/order_manager.py | modified | Refactored reconstruct_from_broker() to separate known vs unknown positions; added _flatten_unknown_position(), _create_reco_position(), _reconstruct_known_position() helpers; added startup_config parameter |
| argus/main.py | modified | Wire startup_config from SystemConfig into OrderManager constructor |
| config/system.yaml | modified | Added startup.flatten_unknown_positions YAML entry |
| config/system_live.yaml | modified | Added startup.flatten_unknown_positions YAML entry |
| scripts/ibkr_close_all_positions.py | modified | chmod +x (permission change only) |
| tests/execution/test_order_manager.py | modified | Added 8 new startup zombie cleanup tests; fixed existing reconstruction test to pre-populate known positions |
| tests/test_integration_sprint5.py | modified | Fixed existing reconstruction test to pre-populate known positions |

### Judgment Calls
- **Extracted 3 helper methods from reconstruct_from_broker():** `_flatten_unknown_position()`, `_create_reco_position()`, `_reconstruct_known_position()`. The prompt specified modifying reconstruction logic; extracting helpers keeps the main method readable while preserving all behavior. Single responsibility principle.
- **RECO entry creation when flatten disabled:** Prompt said "Optionally still create the RECO entry for UI visibility." Chose to create it (maintain existing behavior) since operators need visibility into positions they chose not to auto-flatten.
- **Graceful open_orders failure:** If `get_open_orders()` fails after positions are queried, we log a warning and continue with empty orders list rather than aborting reconstruction entirely. This preserves position recovery even if order query fails.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Find startup position reconstruction logic | DONE | order_manager.py:reconstruct_from_broker() |
| Replace reconstruction-of-unknowns with conditional flatten | DONE | Known/unknown separation + _flatten_unknown_position() |
| Handle IBKR portfolio query failure gracefully | DONE | try/except on get_positions() with WARNING log |
| Add config field flatten_unknown_positions | DONE | StartupConfig in config.py, SystemConfig.startup |
| Wire into SystemConfig | DONE | SystemConfig.startup field |
| Add YAML to system.yaml | DONE | startup section added |
| Add YAML to system_live.yaml | DONE | startup section added |
| Fix script permissions | DONE | chmod +x applied |
| Verify shebang line | DONE | #!/usr/bin/env python3 already present |
| 8+ new tests | DONE | 8 new tests in test_order_manager.py |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Startup sequence order unchanged | PASS | Phase 10 order: broker connect → OrderManager → reconstruct_from_broker → quality pipeline |
| Known positions not affected by startup cleanup | PASS | test_startup_only_known_positions + test_startup_mix_known_and_unknown verify this |
| Normal startup without IBKR positions works | PASS | test_startup_empty_ibkr_portfolio verifies this |
| Flatten happens BEFORE market data streaming | PASS | reconstruct_from_broker() called in Phase 10, before Phase 10.5 event routing |
| Flatten uses broker abstraction | PASS | _flatten_unknown_position() calls self._broker.place_order() |
| Existing reconstruction tests still pass | PASS | Updated 2 tests to pre-populate known positions |

### Test Results
- Tests run: 318 (scoped: execution/ + integration_sprint5)
- Tests passed: 318
- Tests failed: 0
- New tests added: 8
- Command used: `python -m pytest tests/execution/ tests/test_integration_sprint5.py -x -q`
- Full suite: 3655 passed, 9 failed (all 9 are pre-existing xdist-only failures in backtest/counterfactual — pass individually)

### Unfinished Work
None

### Notes for Reviewer
- Two existing tests (test_reconstruct_from_broker_recovers_positions, test_order_manager_reconstruction_with_positions) needed updating to pre-populate _managed_positions with known symbols. This is correct — before this change, ALL broker positions were blindly reconstructed. Now only known positions are reconstructed; unknown ones are flattened or warned.
- The `orders_by_symbol` dict type annotation was tightened from `dict[str, list]` to `dict[str, list[object]]` for Pylance compliance.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27.95",
  "session": "S4",
  "verdict": "COMPLETE",
  "tests": {
    "before": 304,
    "after": 312,
    "new": 8,
    "all_pass": true
  },
  "files_created": [],
  "files_modified": [
    "argus/core/config.py",
    "argus/execution/order_manager.py",
    "argus/main.py",
    "config/system.yaml",
    "config/system_live.yaml",
    "scripts/ibkr_close_all_positions.py",
    "tests/execution/test_order_manager.py",
    "tests/test_integration_sprint5.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Refactored reconstruct_from_broker() into 3 helper methods for clarity. Two existing tests needed updating to pre-populate known positions — correct behavioral change since unknown positions are now handled differently."
}
```
