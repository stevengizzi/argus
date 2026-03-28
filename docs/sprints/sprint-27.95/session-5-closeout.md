---BEGIN-CLOSE-OUT---

**Session:** Sprint 27.95 S5 — Carry-Forward Cleanup
**Date:** 2026-03-28
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/core/config.py | modified | Added StartupConfig model (S4 restore), stop_cancel_retry_max field on OrderManagerConfig (S5 Fix 3), startup field on SystemConfig |
| argus/execution/order_manager.py | modified | Restored S4 zombie cleanup (reconstruct_from_broker refactor, _flatten_unknown_position, _create_reco_position, _reconstruct_known_position, startup_config param); S5 Fix 1 zero-qty guard; S5 Fix 2 direct attribute access on normal close; S5 Fix 3 _resubmit_stop_with_retry uses stop_cancel_retry_max |
| argus/main.py | modified | Restored S4 startup_config wiring to OrderManager constructor |
| config/order_manager.yaml | modified | Added stop_cancel_retry_max: 3 (S5 Fix 3) |
| config/system.yaml | modified | Added startup section with flatten_unknown_positions (S4 restore) |
| config/system_live.yaml | modified | Added startup section with flatten_unknown_positions (S4 restore) |
| tests/execution/test_order_manager.py | modified | Added 11 startup zombie cleanup tests (S4 restore + S5 zero-qty guard test) |
| tests/execution/test_order_manager_hardening.py | modified | Added cancel retry config split test (S5 Fix 3) |
| tests/core/test_config.py | modified | Added 6 config split + YAML alignment tests (S5 Fix 3) |

### Judgment Calls
- **S4 restoration required:** S3b (800695b) overwrote all S4 changes to order_manager.py, config.py, main.py, and YAML files. The entire S4 refactor (zombie classification, helpers, StartupConfig, main.py wiring) had to be re-applied before S5 fixes could be layered on. This was necessary but outside the S5 spec scope.
- **stop_cancel_retry_max added to order_manager.yaml:** The spec said "Add to config/system.yaml and config/system_live.yaml" but OrderManager config lives in a separate `config/order_manager.yaml` file. Added to the correct file instead.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Zero-qty guard before _flatten_unknown_position | DONE | order_manager.py:reconstruct_from_broker — abs(qty) <= 0 guard with DEBUG log |
| Normal close uses direct attribute access | DONE | order_manager.py:_close_position — position.original_stop_price etc. |
| Reconciliation close keeps getattr with fallback | DONE | order_manager.py:_close_position — getattr with defensive comment |
| stop_cancel_retry_max added to OrderManagerConfig | DONE | config.py:OrderManagerConfig — Field(default=3, ge=0) with inline comment |
| _resubmit_stop_with_retry uses stop_cancel_retry_max | DONE | order_manager.py:_resubmit_stop_with_retry — both references updated |
| Log messages reference new config field name | DONE | Log format string uses stop_cancel_retry_max |
| YAML files updated with new field | DONE | config/order_manager.yaml (not system.yaml — see judgment calls) |
| All existing tests pass | DONE | 417 passed (scoped) |
| 4+ new tests written | DONE | 18 new tests (11 execution + 1 hardening + 6 config) |
| Close-out report written | DONE | This file |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Normal close path produces correct stop/t1/t2 values | PASS | Existing trade logging tests pass |
| Reconciliation close still works with defensive defaults | PASS | test_order_manager_reconciliation_redesign.py passes |
| Stop retry cap triggers emergency flatten at correct threshold | PASS | test_order_manager_hardening.py passes |
| Startup zombie cleanup correctly flattens non-zero-qty zombies | PASS | test_startup_flatten_unknown_positions_enabled passes |
| Startup zombie cleanup skips zero-qty positions | PASS | test_startup_zero_qty_zombie_skips_flatten passes |
| _submit_stop_order still uses stop_retry_max | PASS | Confirmed via grep: lines 1539, 1563, 1568 |
| _resubmit_stop_with_retry uses stop_cancel_retry_max | PASS | Confirmed via grep: lines 600, 616 |

### Test Results
- Tests run: 417 (scoped: execution/ + core/test_config.py)
- Tests passed: 417
- Tests failed: 0
- New tests added: 18 (11 startup zombie + 1 cancel retry config + 6 config alignment)
- Command used: `python -m pytest tests/execution/ tests/core/test_config.py -x -q`

### Unfinished Work
None — all spec items complete.

### Notes for Reviewer
- **S4 restoration is the biggest change:** S3b (800695b) overwrote all S4 order_manager.py changes. The S4 refactor (zombie detection via broker orders, 3 extracted helper methods, StartupConfig, main.py wiring) had to be fully restored before S5 fixes could be applied. This is a larger diff than the S5 spec alone would suggest.
- **Config YAML location:** stop_cancel_retry_max was added to `config/order_manager.yaml` (the actual config file for OrderManagerConfig) rather than system.yaml/system_live.yaml (which don't have order_manager sections).
- **Context state:** GREEN — session completed well within context limits.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27.95",
  "session": "S5",
  "verdict": "COMPLETE",
  "tests": {
    "before": 304,
    "after": 315,
    "new": 18,
    "all_pass": true
  },
  "files_created": [],
  "files_modified": [
    "argus/core/config.py",
    "argus/execution/order_manager.py",
    "argus/main.py",
    "config/order_manager.yaml",
    "config/system.yaml",
    "config/system_live.yaml",
    "tests/execution/test_order_manager.py",
    "tests/execution/test_order_manager_hardening.py",
    "tests/core/test_config.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "Restored all S4 changes (StartupConfig, zombie detection, helpers, YAML, main.py wiring) that were lost when S3b overwrote order_manager.py",
      "justification": "S3b (800695b) clobbered S4 changes — S5 fixes depend on S4 infrastructure existing"
    }
  ],
  "scope_gaps": [],
  "prior_session_bugs": [
    {
      "description": "S3b (800695b) overwrote all S4 changes to order_manager.py, config.py, main.py, and YAML files",
      "affected_session": "S4",
      "affected_files": ["argus/execution/order_manager.py", "argus/core/config.py", "argus/main.py", "config/system.yaml", "config/system_live.yaml"],
      "severity": "HIGH",
      "blocks_sessions": []
    }
  ],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "S3b (800695b) used the S2 version of order_manager.py as its base and overwrote all S4 changes. This was likely caused by S3b being implemented in a separate context that branched from S2 rather than S4. All S4 code had to be manually restored from git show d93a1bd before S5 fixes could be applied."
}
```
