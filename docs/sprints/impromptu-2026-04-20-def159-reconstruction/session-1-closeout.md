---BEGIN-CLOSE-OUT---

**Session:** Impromptu DEF-159 — Reconstruction Trade Logging Fix
**Date:** 2026-04-20
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/db/schema.sql | modified | Added entry_price_known column definition |
| argus/db/manager.py | modified | Added ALTER TABLE migration for entry_price_known |
| argus/models/trading.py | modified | Added entry_price_known field to Trade model |
| argus/analytics/trade_logger.py | modified | INSERT includes entry_price_known; read-back; filters in get_todays_pnl, get_todays_trade_count, get_daily_summary |
| argus/analytics/performance.py | modified | compute_metrics filters out entry_price_known=0 trades |
| argus/execution/order_manager.py | modified | _close_position sets entry_price_known=False when entry_price==0.0 |
| scripts/migrate_def159_bogus_trades.py | added | One-shot migration script to mark existing bogus rows |
| tests/analytics/test_def159_entry_price_known.py | added | 4 regression tests for the fix |
| CLAUDE.md | modified | DEF-159 marked RESOLVED |
| docs/sprint-history.md | modified | Added impromptu entry + updated statistics |

### Judgment Calls
- Chose Option B (boolean column `entry_price_known`) over Option A (nullable entry_price) or Option C (composite filter). Rationale: explicit, self-documenting, minimal blast radius (no change to entry_price semantics), no risk of breaking existing queries that assume entry_price is NOT NULL.
- Used `entry_price == 0.0` as the detection heuristic in `_close_position()` rather than checking strategy_id=="reconstructed". This is safer because any future code path that produces a 0.0 entry will be correctly marked, not just the reconstruction path.
- The prompt expected 28 bogus rows; actual count was 10. No escalation needed (threshold was >50).

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Mark reconstructed trades with unrecoverable entry | DONE | entry_price_known column + order_manager.py detection |
| Analytics consumers respect marker | DONE | performance.py, trade_logger.py (4 methods) |
| One-shot migration script | DONE | scripts/migrate_def159_bogus_trades.py |
| Mark existing bogus rows (28 expected, 10 actual) | DONE | 10 rows updated |
| 3+ regression tests | DONE | 4 tests in test_def159_entry_price_known.py |
| Full test suite passes | DONE | 4,919 passed |
| DEF-159 marked RESOLVED | DONE | CLAUDE.md updated |
| Sprint-history entry | DONE | docs/sprint-history.md updated |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Normal trade logging unchanged | PASS | Existing test_trade_logger tests pass |
| Normal reconstruction path unchanged | PASS | Existing test_trade_logger_reconciliation tests pass |
| Performance calculator handles marker | PASS | New test verifies filter |
| Dashboard/debrief don't crash | PASS | All API tests pass |
| DEF-158 fix intact | PASS | test_order_manager_def158.py 5/5 pass |
| Impromptu A/B/C files untouched | PASS | Only order_manager.py touched (1 line addition per constraint) |
| Sprint 31.75 files untouched | PASS | No changes to experiments/, historical_query, etc. |
| 10 bogus rows marked correctly | PASS | Verified via sqlite3 query |

### Test Results
- Tests run: 4,919
- Tests passed: 4,919
- Tests failed: 0
- New tests added: 4
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`

### Unfinished Work
None

### Notes for Reviewer
- The order_manager.py change is minimal (1 line: `entry_known = position.entry_price != 0.0` + adding it to the Trade constructor). This is within the constraint that allows "minimum necessary change" to the reconstruction call site.
- The migration found 10 rows (not 28 as the prompt expected). All 10 share identical characteristics: strategy_id="reconstructed", entry_price=0.0, exit_reason="time_stop", outcome="win". The prompt's "28" was likely an overestimate based on the total zombie positions seen in logs (some of which may have been flattened without trade logging).

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "Impromptu DEF-159",
  "session": "S1",
  "verdict": "COMPLETE",
  "tests": {
    "before": 5761,
    "after": 5765,
    "new": 4,
    "all_pass": true,
    "pytest_count": 4919,
    "vitest_count": 846
  },
  "files_created": [
    "scripts/migrate_def159_bogus_trades.py",
    "tests/analytics/test_def159_entry_price_known.py"
  ],
  "files_modified": [
    "argus/db/schema.sql",
    "argus/db/manager.py",
    "argus/models/trading.py",
    "argus/analytics/trade_logger.py",
    "argus/analytics/performance.py",
    "argus/execution/order_manager.py",
    "CLAUDE.md",
    "docs/sprint-history.md"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "Future improvement: query IBKR executions API during reconstruction to recover actual entry prices rather than just marking them unknown"
  ],
  "doc_impacts": [
    {"document": "CLAUDE.md", "change_description": "DEF-159 marked RESOLVED"},
    {"document": "docs/sprint-history.md", "change_description": "Added impromptu entry and updated statistics"}
  ],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Chose Option B (boolean column) for smallest blast radius. Detection uses entry_price==0.0 rather than strategy_id check for broader coverage. Actual bogus row count was 10 (not 28 as estimated in prompt)."
}
```
