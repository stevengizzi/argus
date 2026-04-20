---BEGIN-CLOSE-OUT---

**Session:** Impromptu 2026-04-20 (C) — DEF-158 Duplicate SELL Bug Fix
**Date:** 2026-04-20
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/execution/order_manager.py | modified | 4 methods fixed: `_check_flatten_pending_timeouts` (broker position query before resubmit), `_flatten_unknown_position` (cancel pre-existing orders), `_handle_stop_fill` (cancel concurrent flatten), `_handle_flatten_fill` (cancel duplicate flattens) |
| tests/execution/test_order_manager_def158.py | added | 5 regression tests covering all 3 root causes + positive resubmit case |
| CLAUDE.md | modified | DEF-158 resolved, DEF-159 logged (stretch deferred), DEF-160 logged (no fix) |
| docs/sprint-history.md | modified | AU entry for DEF-158 impromptu |
| dev-logs/2026-04-20_duplicate-sell.md | added | Dev log with root cause analysis |
| docs/sprints/impromptu-2026-04-20-duplicate-sell/session-1-closeout.md | added | This file |

### Judgment Calls
- **Always query broker instead of only on error_404:** The old code only queried broker position when `error_404_symbols` was flagged. The new code always queries, since the IBKR fill callback delay is the core problem, not specific error codes. Preserved `error_404_symbols.discard()` for backwards compatibility with Sprint 29.5 R1 test expectations.
- **Deferred DEF-159 (stretch goal):** The prompt specified DEF-159 as stretch only. DEF-158 is fully resolved with 5 tests. DEF-159 (reconstructed trades with entry_price=0.00) is logged for a follow-up session.
- **Cancel via get_open_orders in startup cleanup:** Used `get_open_orders()` + per-symbol filter rather than `reqGlobalCancel()` because global cancel would affect orders for ALL symbols, not just the zombie being flattened.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| R1: Diagnose DEF-158 root cause | DONE | 3 root causes identified with evidence, file:line references, and ARX/DHR case study |
| R2: Fix DEF-158 | DONE | 4 method changes in order_manager.py |
| R2: 3+ regression tests | DONE | 5 tests in test_order_manager_def158.py |
| R2: DEF-158 RESOLVED in CLAUDE.md | DONE | Full root cause explanation |
| R3: DEF-159 stretch | DEFERRED | Logged as DEF-159 in CLAUDE.md, not attempted (stretch budget) |
| R4: Log DEF-160 | DONE | Added to CLAUDE.md deferred items table |
| Sprint-history entry AU | DONE | docs/sprint-history.md |
| Dev-log | DONE | dev-logs/2026-04-20_duplicate-sell.md |
| Close-out | DONE | This file |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Normal bracket fill path unchanged | PASS | Existing test_order_manager bracket tests pass |
| Normal EOD flatten unchanged | PASS | test_order_manager EOD tests pass |
| Normal reconciliation unchanged | PASS | test_order_manager_reconciliation tests pass |
| Startup zombie cleanup still flattens | PASS | _flatten_unknown_position still places SELL after cancelling orders |
| Duplicate fill dedup (DEC-374) still works | PASS | on_fill dedup logic unchanged |
| Morning session files untouched | PASS | git diff shows no changes to server.py, main.py, start_live.sh, telemetry_store.py |
| Sprint 31.75 files untouched | PASS | No changes to experiments/, historical_query_service.py, etc. |
| No strategy file modifications | PASS | git diff argus/strategies/ empty |

### Test Results
- **Before:** 4,910 pytest + 846 Vitest = 5,756 total
- **After:** 4,915 pytest + 846 Vitest = 5,761 total
- **New:** 5 tests
- **All passing:** Yes
- **Command:** `python -m pytest --ignore=tests/test_main.py -n auto -q`

### Unfinished Work
- DEF-159 (reconstructed flatten trades with entry_price=0.00 logged as wins): Deferred to follow-up session as specified in prompt (stretch goal only if budget remains).

### Notes for Reviewer
- The 3 root causes are independent but compound: any one of them alone could produce a short position, but all three acting together during today's incident amplified the damage to 28 symbols.
- The fix is conservative: each guard independently prevents its respective failure mode without relying on the others.
- The `_check_flatten_pending_timeouts` change adds a broker query on every timeout, which is an additional API call every 120s per stale flatten. Acceptable cost for preventing shorts.
- No DEC behavior was rolled back. The flatten-pending timeout mechanism (Sprint 28.75 R2) still works — it just verifies broker state first.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "impromptu-2026-04-20-duplicate-sell",
  "session": "S1",
  "verdict": "COMPLETE",
  "tests": {
    "before": 5756,
    "after": 5761,
    "new": 5,
    "all_pass": true,
    "pytest_count": 4915,
    "vitest_count": 846
  },
  "files_created": [
    "tests/execution/test_order_manager_def158.py",
    "dev-logs/2026-04-20_duplicate-sell.md",
    "docs/sprints/impromptu-2026-04-20-duplicate-sell/session-1-closeout.md"
  ],
  "files_modified": [
    "argus/execution/order_manager.py",
    "CLAUDE.md",
    "docs/sprint-history.md"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "DEF-159: Reconstructed flatten trades logged with entry_price=0.00 as wins — deferred to follow-up session"
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Three independent root causes identified and fixed. The primary cause (flatten-pending timeout resubmission when IBKR delays fill callbacks) explains the 120s gap between duplicate SELLs seen in the ARX timeline. The startup cleanup cause explains why afternoon boot placed additional SELLs on already-flat positions. The stop-fill cause is a general race condition that could also produce shorts independently."
}
```
