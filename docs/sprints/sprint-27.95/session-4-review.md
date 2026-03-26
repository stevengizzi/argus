---BEGIN-REVIEW---

**Reviewing:** Sprint 27.95 S4 -- Startup Zombie Cleanup
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-27
**Verdict:** ESCALATE

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All spec requirements implemented. No forbidden directories touched. |
| Close-Out Accuracy | PASS | Change manifest matches diff. Judgment calls documented. |
| Test Health | PASS | 318/318 scoped tests pass. 3653/3664 full suite pass (11 pre-existing failures). |
| Regression Checklist | FAIL | Known positions NOT preserved on normal restart -- see Finding F-001. |
| Architectural Compliance | PASS | Uses broker abstraction, Pydantic config, proper typing. |
| Escalation Criteria | TRIGGERED: #1 | Startup flatten closes positions that should be kept. |

### Findings

**F-001 [CRITICAL] -- All broker positions classified as "unknown" at boot, would be flattened on restart**

The matching logic in `reconstruct_from_broker()` (order_manager.py line 1311) determines "known" vs "unknown" positions by checking `self._managed_positions.keys()`:

```python
known_symbols = set(self._managed_positions.keys())
```

However, `_managed_positions` is initialized as an empty dict in `__init__` (line 196) and nothing populates it before `reconstruct_from_broker()` is called in the startup sequence. In `main.py`, the call order is:

- Phase 10: `OrderManager()` constructor (empty `_managed_positions`)
- Phase 10: `order_manager.start()` (subscribes to events, starts poll loop -- does NOT load positions)
- Phase 10: `order_manager.reconstruct_from_broker()` (checks empty `_managed_positions`)

At this point, `known_symbols` is always an empty set. Therefore ALL broker positions -- including legitimate positions from a prior ARGUS session that survived a crash/restart -- would be classified as "unknown" and flattened.

This directly triggers escalation criterion #1: "Startup flatten closes positions that should be kept -- halt, fix matching logic."

The tests mask this issue because they manually pre-populate `om._managed_positions["AAPL"] = []` before calling `reconstruct_from_broker()`, simulating a state that never occurs in the actual production startup sequence.

**Impact:** On any mid-session restart (crash recovery, manual restart), all real positions would be immediately sold at market. This is a safety-critical issue affecting real money.

**Root cause:** The "known positions" concept requires some source of truth (database, prior state file, or the broker itself) to exist before the broker query. The current design has no such source. The old behavior (reconstruct everything) was correct for the restart case. The new behavior should only flatten positions that are genuinely orphaned (e.g., from a completely different prior session that did not shut down cleanly).

**Possible fixes:**
1. Load position state from the database (TradeLogger) before `reconstruct_from_broker()` to populate `_managed_positions` with positions that have no close record.
2. Add a "last session ID" or timestamp check -- positions from the current day's session are considered known.
3. Only flatten positions for symbols that have never been traded by ARGUS (check trade history).
4. Require a "previous session clean shutdown" flag -- if the last shutdown was clean (all positions closed), then any broker positions are truly zombies. If not, they are likely crash-recovery positions.

**F-002 [LOW] -- Close-out reports 9 pre-existing failures but full suite shows 11**

The close-out states "3655 passed, 9 failed (all 9 are pre-existing xdist-only failures)." The actual full suite result is 3653 passed, 11 failed. The 2 additional failures (`test_teardown_cleans_up`, `test_empty_data_returns_empty_result` in test_engine.py) are confirmed pre-existing (they fail on the prior commit as well). This is a minor close-out inaccuracy, not a regression.

**F-003 [INFO] -- RECO position created when flatten disabled has no stop protection**

When `flatten_unknown_positions=False`, `_create_reco_position()` creates a ManagedPosition with `stop_price=0.0` and no bracket orders. This position would not be protected by a stop loss. This is acceptable for the "warn only" path since the operator is expected to handle it manually, but worth noting for documentation.

### Recommendation

ESCALATE to Tier 3 architectural review. Finding F-001 is a safety-critical bug in the position matching logic. The `_managed_positions` dict is always empty when `reconstruct_from_broker()` runs at startup, causing ALL broker positions to be classified as "unknown" and flattened. This would destroy legitimate positions on any mid-session restart.

The fix requires establishing a source of truth for "what positions did ARGUS have open" before the broker query. This likely involves querying the trades database for positions with no close record, or restructuring the startup sequence to load position state from persistent storage first.

Do NOT deploy this change to live trading until the matching logic is corrected.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.95",
  "session": "S4",
  "verdict": "ESCALATE",
  "findings": [
    {
      "description": "All broker positions classified as 'unknown' at boot because _managed_positions is always empty when reconstruct_from_broker() runs. On any mid-session restart, all real positions would be flattened (sold at market). Tests mask this by manually pre-populating _managed_positions.",
      "severity": "CRITICAL",
      "category": "REGRESSION",
      "file": "argus/execution/order_manager.py",
      "recommendation": "Load position state from database (trades with no close record) before reconstruct_from_broker(), or restructure matching logic to use a persistent source of truth."
    },
    {
      "description": "Close-out reports 9 pre-existing test failures but actual count is 11. Two additional failures in test_engine.py are confirmed pre-existing.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "docs/sprints/sprint-27.95/session-4-closeout.md",
      "recommendation": "Correct the close-out failure count for accuracy."
    },
    {
      "description": "RECO position created when flatten disabled has stop_price=0.0 and no bracket protection.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "argus/execution/order_manager.py",
      "recommendation": "Document in operator notes that RECO positions require manual stop placement."
    }
  ],
  "spec_conformance": {
    "status": "MAJOR_DEVIATION",
    "notes": "Implementation matches spec literally but the spec's concept of 'known positions' has no backing data source at startup, making the matching logic vacuous.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/core/config.py",
    "argus/execution/order_manager.py",
    "argus/main.py",
    "config/system.yaml",
    "config/system_live.yaml",
    "tests/execution/test_order_manager.py",
    "tests/test_integration_sprint5.py",
    "docs/sprints/sprint-27.95/session-4-closeout.md"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 318,
    "new_tests_adequate": false,
    "test_quality_notes": "Tests pre-populate _managed_positions manually, creating a state that never occurs in production startup. Tests pass but do not verify the real startup flow where _managed_positions is empty."
  },
  "regression_checklist": {
    "all_passed": false,
    "results": [
      {"check": "Startup sequence unchanged for normal operation", "passed": true, "notes": "Phase 10 order preserved."},
      {"check": "Known positions preserved", "passed": false, "notes": "CRITICAL: _managed_positions is empty at boot; all positions treated as unknown and flattened."},
      {"check": "Config field recognized by Pydantic", "passed": true, "notes": "StartupConfig model works correctly."},
      {"check": "Full test suite passes, no hangs", "passed": true, "notes": "3653 passed, 11 pre-existing failures, no hangs."}
    ]
  },
  "escalation_triggers": [
    "Startup flatten closes positions that should be kept -- _managed_positions empty at boot means ALL broker positions are classified as unknown"
  ],
  "recommended_actions": [
    "Fix matching logic to use a persistent source of truth (database query for open positions) before broker reconciliation",
    "Add an integration test that simulates the real startup sequence (empty _managed_positions) with broker positions present",
    "Do NOT deploy to live trading until matching logic is corrected"
  ]
}
```
