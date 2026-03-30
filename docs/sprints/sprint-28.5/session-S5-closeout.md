```markdown
---BEGIN-CLOSE-OUT---

**Session:** Sprint 28.5 S5 — BacktestEngine + CounterfactualTracker Alignment
**Date:** 2026-03-30
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/backtest/engine.py | modified | Added _BacktestPosition dataclass, exit config loading, AMD-7 bar-processing with trail/escalation state |
| argus/intelligence/counterfactual.py | modified | Added trail/escalation fields to _OpenPosition, AMD-7 bar-processing in _process_bar, exit_configs constructor param |
| tests/backtest/test_engine_exit_management.py | added | 14 tests for BacktestEngine trail/escalation state and AMD-7 ordering |
| tests/intelligence/test_counterfactual_exit_management.py | added | 7 tests for CounterfactualTracker trail/escalation state and AMD-7 ordering |

### Judgment Calls
- **_BacktestPosition as parallel state**: Created a separate `_BacktestPosition` dataclass in engine.py rather than modifying ManagedPosition or accessing OrderManager internals. ManagedPosition already has trail fields (from S4a), but BacktestEngine's bar-level processing needs its own state management since OrderManager.on_tick() is never called in backtest mode. This keeps concerns separated.
- **Exit config cache omitted for BacktestEngine**: Unlike OrderManager which caches merged per-strategy configs, BacktestEngine recomputes on each `_get_exit_config` call. Acceptable because it's only called once per position creation (not per bar).
- **CounterfactualTracker exit_configs parameter**: Added as constructor parameter (dict keyed by strategy_id) rather than passing through metadata or adding a setter. This mirrors how the tracker already receives other configuration.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| BacktestPosition extended with trail/escalation state | DONE | engine.py:_BacktestPosition dataclass (lines 90-127) |
| ShadowPosition extended with trail/escalation state | DONE | counterfactual.py:_OpenPosition (6 new fields, lines 144-149) |
| AMD-7 bar-processing order in BacktestEngine | DONE | engine.py:_check_bracket_orders (Step 1→2→3 ordering) |
| AMD-7 bar-processing order in CounterfactualTracker | DONE | counterfactual.py:_process_bar (Step 1→2→3 ordering) |
| ExitManagementConfig loading in BacktestEngine | DONE | engine.py:_load_exit_management_config, passed to OrderManager |
| ExitManagementConfig loading in CounterfactualTracker | DONE | counterfactual.py:exit_configs constructor param |
| Non-trail behavior bit-identical | DONE | Tests #5 and #11 verify default/disabled configs produce original stop |
| 13+ new tests | DONE | 21 new tests (14 engine + 7 counterfactual) |
| fill_model.py NOT modified | DONE | git diff confirms zero changes |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| BacktestEngine non-trail identical | PASS | Test #5 verifies default config produces original stop |
| CounterfactualTracker non-trail identical | PASS | Test #11 verifies no-config and disabled-config use original stop |
| fill_model.py not modified | PASS | git diff shows no changes |
| AMD-7 ordering correct | PASS | Test #7 verifies prior state used, not current bar's updated state |
| All existing backtest tests pass | PASS | 630 scoped tests pass (0 regressions) |
| All existing counterfactual tests pass | PASS | Included in scoped and full suite |
| Full test suite passes | PASS | 3,955 passed in 53s |

### Test Results
- Tests run: 3,955
- Tests passed: 3,955
- Tests failed: 0
- New tests added: 21
- Command used: `python -m pytest --ignore=tests/test_main.py -x -q -n auto`

### Unfinished Work
None

### Notes for Reviewer
- **AMD-7 is the critical correctness property**: The effective stop MUST be computed from PRIOR bar's trail/escalation state, not updated from the current bar's high. Test #7 specifically validates this with numeric values: prior trail=$49.50 (correct exit price) vs updated trail=$51.0 (wrong price).
- **BacktestEngine uses _bt_positions dict**: Parallel to ManagedPosition's trail fields. The engine synchronizes state from ManagedPosition on first encounter and syncs T1 fills for after_t1 activation. The dict is cleared on each daily reset.
- **CounterfactualTracker backfill**: Trail state updates through each backfill bar in sequence. If trail triggers during backfill, the break at line 275 (`if position_id not in self._open_positions: break`) correctly stops processing. Test #13 verifies this.
- **No changes to Order Manager**: All exit management logic in the engine is independent of the Order Manager's tick-based trail/escalation (which runs in live mode only).

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "28.5",
  "session": "S5",
  "verdict": "COMPLETE",
  "tests": {
    "before": 3934,
    "after": 3955,
    "new": 21,
    "all_pass": true
  },
  "files_created": [
    "tests/backtest/test_engine_exit_management.py",
    "tests/intelligence/test_counterfactual_exit_management.py"
  ],
  "files_modified": [
    "argus/backtest/engine.py",
    "argus/intelligence/counterfactual.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Created _BacktestPosition dataclass as parallel trail state tracker rather than modifying ManagedPosition. BacktestEngine loads exit_management.yaml and per-strategy overrides using same pattern as main.py. CounterfactualTracker receives exit_configs via constructor dict. Both engines implement AMD-7 ordering: prior state → evaluate → update."
}
```
