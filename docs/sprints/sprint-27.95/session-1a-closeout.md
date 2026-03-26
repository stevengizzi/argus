---BEGIN-CLOSE-OUT---

**Session:** Sprint 27.95 — Session 1a: Reconciliation Redesign
**Date:** 2026-03-26
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/core/config.py` | modified | Added `ReconciliationConfig` Pydantic model with `auto_cleanup_unconfirmed` and `consecutive_miss_threshold` fields; wired into `SystemConfig` |
| `argus/execution/order_manager.py` | modified | Added `_broker_confirmed` and `_reconciliation_miss_count` dicts; redesigned `reconcile_positions()` with 3-branch logic; cleanup in `_close_position` and `reset_daily_state`; accepts `ReconciliationConfig` param |
| `argus/main.py` | modified | Replaced raw YAML dict reading with typed `config.system.reconciliation` Pydantic config for OrderManager construction |
| `config/system.yaml` | modified | Added `reconciliation:` section with `auto_cleanup_orphans: false`, `auto_cleanup_unconfirmed: false`, `consecutive_miss_threshold: 3` |
| `config/system_live.yaml` | modified | Added `reconciliation:` section with `auto_cleanup_orphans: true`, `auto_cleanup_unconfirmed: true`, `consecutive_miss_threshold: 3` |
| `tests/execution/test_order_manager_reconciliation.py` | modified | Updated 2 existing tests to inject unconfirmed positions directly (reflecting new behavior: confirmed positions are never auto-closed) |
| `tests/execution/test_order_manager_reconciliation_redesign.py` | added | 13 new tests covering all reconciliation redesign requirements |

### Judgment Calls
- **Legacy backwards compatibility:** Added `reconciliation_config` parameter to `OrderManager.__init__()` with fallback from legacy `auto_cleanup_orphans` bool param. This preserves existing call sites that pass `auto_cleanup_orphans=True/False` without requiring immediate migration.
- **Existing test adaptation:** Two existing tests (`test_reconciliation_cleanup_closes_orphan`, `test_reconciliation_cleanup_sets_zero_pnl`) were updated to inject unconfirmed positions directly instead of using `_open_position()` (which sets `_broker_confirmed=True`). This reflects the intentional behavioral change where confirmed positions are NEVER auto-closed.
- **`auto_cleanup_orphans` still works for unconfirmed positions:** Legacy `auto_cleanup_orphans=True` triggers immediate cleanup of unconfirmed positions (no miss threshold). This preserves the Sprint 27.8 behavior for callers that don't adopt the new config model.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| `_broker_confirmed: dict[str, bool]` tracking | DONE | `order_manager.py:__init__` |
| Set `_broker_confirmed[symbol] = True` on entry fill | DONE | `order_manager.py:_handle_entry_fill` |
| Clean up `_broker_confirmed` on position close | DONE | `order_manager.py:_close_position` |
| `_reconciliation_miss_count: dict[str, int]` tracking | DONE | `order_manager.py:__init__` |
| Clean up miss count on position close | DONE | `order_manager.py:_close_position` |
| Confirmed positions: WARNING + never auto-close | DONE | `order_manager.py:reconcile_positions` branch 1 |
| Unconfirmed + `auto_cleanup_unconfirmed`: miss counter + threshold | DONE | `order_manager.py:reconcile_positions` branch 2 |
| Unconfirmed + cleanup disabled: warn-only | DONE | `order_manager.py:reconcile_positions` branch 3/4 |
| Reset miss counter when position found in snapshot | DONE | `order_manager.py:reconcile_positions` snapshot-present path |
| `ReconciliationConfig` Pydantic model with `auto_cleanup_unconfirmed` + `consecutive_miss_threshold` | DONE | `config.py:ReconciliationConfig` |
| `consecutive_miss_threshold` validator `ge=1` | DONE | `config.py:ReconciliationConfig` |
| Wire into `SystemConfig` | DONE | `config.py:SystemConfig.reconciliation` |
| YAML entries in `system.yaml` and `system_live.yaml` | DONE | Both files updated |
| 10+ new tests | DONE | 13 new tests in `test_order_manager_reconciliation_redesign.py` |
| Config validation test (YAML keys match model fields) | DONE | `test_reconciliation_config_yaml_keys_match_model` |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Normal position lifecycle unchanged | PASS | All existing position lifecycle tests pass |
| Entry fill still triggers "Position opened" log | PASS | `_handle_entry_fill` unchanged except adding `_broker_confirmed` set |
| Position close cleans up all tracking state | PASS | Tests 8+9 verify `_broker_confirmed` and `_reconciliation_miss_count` cleanup |
| Reconciliation mismatch summary logging preserved | PASS | Existing `test_reconciliation_summary_single_line` passes |
| `_flatten_pending` guard intact | PASS | No modifications to flatten guard logic |
| Bracket amendment logic intact | PASS | No modifications to bracket amendment logic |
| EOD flatten still works | PASS | Existing flatten tests pass |
| `auto_cleanup_orphans` legacy path still works | PASS | Test 13 (`test_legacy_auto_cleanup_orphans_still_works`) verifies |

### Test Results
- Tests run: 3,636 (3,628 passed + 8 pre-existing failures)
- Tests passed: 3,628
- Tests failed: 8 (all pre-existing, none from this session)
- New tests added: 13
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`

Pre-existing failures (confirmed on clean HEAD before changes):
1. `tests/api/test_server_intelligence.py::test_lifespan_ai_disabled_catalyst_enabled`
2. `tests/ai/test_client.py::TestClaudeClientDisabled::test_send_message_returns_graceful_response`
3. `tests/ai/test_client.py::TestClaudeClientDisabled::test_send_with_tool_results_returns_graceful_response`
4. `tests/ai/test_client.py::TestClaudeClientDisabled::test_streaming_returns_error_event_when_disabled`
5. `tests/ai/test_config.py::TestAIConfigDefaults::test_default_values`
6. `tests/intelligence/test_counterfactual_wiring.py::TestBuildCounterfactualTracker::test_store_initialized_with_table`
7. `tests/backtest/test_engine.py::test_teardown_cleans_up`
8. `tests/backtest/test_engine.py::test_empty_data_returns_empty_result`

### Unfinished Work
None

### Notes for Reviewer
- The 8 pre-existing test failures are NOT caused by this session's changes. They were confirmed on clean HEAD before any modifications.
- Two existing tests in `test_order_manager_reconciliation.py` were adapted to reflect the intentional behavioral change: confirmed positions are never auto-closed. The tests now inject unconfirmed positions directly instead of using `_open_position()` (which sets `_broker_confirmed=True`).
- The `reconcile_positions()` method now has 4 branches for orphan handling: (1) confirmed → warn only, (2) unconfirmed + `auto_cleanup_unconfirmed` → miss counter, (3) unconfirmed + `auto_cleanup_orphans` → immediate legacy cleanup, (4) else → warn only.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27.95",
  "session": "S1a",
  "verdict": "COMPLETE",
  "tests": {
    "before": 3618,
    "after": 3636,
    "new": 13,
    "all_pass": false
  },
  "files_created": [
    "tests/execution/test_order_manager_reconciliation_redesign.py",
    "docs/sprints/sprint-27.95/session-1a-closeout.md"
  ],
  "files_modified": [
    "argus/core/config.py",
    "argus/execution/order_manager.py",
    "argus/main.py",
    "config/system.yaml",
    "config/system_live.yaml",
    "tests/execution/test_order_manager_reconciliation.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "8 pre-existing test failures (AI client, AI config, server intelligence, counterfactual wiring, backtest engine) — none caused by this session"
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Legacy auto_cleanup_orphans parameter preserved with backwards-compatible fallback. ReconciliationConfig wraps both old and new fields. Two existing tests adapted to inject unconfirmed positions (behavioral change: confirmed positions are never auto-closed)."
}
```
