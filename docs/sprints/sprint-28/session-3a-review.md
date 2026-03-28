---BEGIN-REVIEW---

# Tier 2 Review: Sprint 28, Session 3a — LearningStore SQLite Persistence

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-28
**Verdict:** CLEAR

## Summary

Session 3a took **Path A** (Adopt + Extend): S4's existing `learning_store.py` was adopted as-is, and 27 new tests were added in `test_learning_store.py`. No production code was changed. This is the expected path per the implementation prompt.

## Change Manifest

| File | Action | Lines |
|------|--------|-------|
| `tests/intelligence/learning/test_learning_store.py` | **Created** | 630 |
| `argus/intelligence/learning/learning_store.py` | Unchanged (S4) | 563 |
| `argus/intelligence/learning/__init__.py` | Unchanged (S4) | 37 |

## Session-Specific Review Focus

### F1: DEC-345 Pattern (WAL mode, fire-and-forget, rate-limited warnings) -- PASS

- **WAL mode:** `PRAGMA journal_mode=WAL` executed in `initialize()` (line 104). Test `test_wal_mode_enabled` verifies.
- **Fire-and-forget writes:** All write methods (`save_report`, `save_proposal`, `update_proposal_status`, `record_change`, `supersede_proposals`, `enforce_retention`) wrap DB operations in `try/except Exception` and call `_rate_limited_warn()` instead of raising. Test `test_save_report_fire_and_forget` verifies.
- **Rate-limited warnings:** `_rate_limited_warn()` (lines 553-563) uses `time.monotonic()` with 60-second interval, matching the DEC-345 pattern from `counterfactual_store.py`.

### F2: Proposal State Machine Matches Amendment 6 -- PASS

The full state machine is: PENDING -> APPROVED/DISMISSED/SUPERSEDED/REJECTED_GUARD/REJECTED_VALIDATION -> APPLIED -> REVERTED.

Tests cover:
- `test_update_proposal_status_approved` (PENDING -> APPROVED)
- `test_full_proposal_state_machine` (PENDING -> APPROVED -> APPLIED -> REVERTED)
- `test_dismissed_and_rejected_statuses` (PENDING -> DISMISSED, REJECTED_GUARD, REJECTED_VALIDATION)
- `test_supersede_proposals_only_pending_from_prior_reports` (PENDING -> SUPERSEDED)
- `test_update_proposal_status_applied_sets_applied_at` (APPLIED sets applied_at)
- `test_update_proposal_status_reverted_sets_reverted_at` (REVERTED sets reverted_at)

Note: The store itself does not enforce valid transitions -- it accepts any status string. This is appropriate; transition enforcement belongs in the ConfigProposalManager (S4), not the persistence layer.

### F3: Retention Enforcement Skips APPLIED/REVERTED Reports (Amendment 11) -- PASS

`enforce_retention()` (lines 228-245) uses a `NOT IN` subquery: `WHERE status IN ('APPLIED', 'REVERTED')`. Three tests verify:
- `test_enforce_retention_deletes_old_reports` -- old unreferenced reports deleted, recent ones kept
- `test_enforce_retention_protects_applied_reverted_reports` -- APPLIED-referenced old report survives
- `test_enforce_retention_protects_reverted_reports` -- REVERTED-referenced old report survives
- `test_enforce_retention_empty_db` -- empty DB returns 0

### F4: Supersession Only Affects PENDING from Prior Reports (Amendment 6) -- PASS

`supersede_proposals()` (lines 411-425) uses `WHERE status = 'PENDING' AND report_id != ?`. Test `test_supersede_proposals_only_pending_from_prior_reports` verifies:
- Old report PENDING proposals become SUPERSEDED (count=1)
- Old report APPROVED proposals untouched
- New report PENDING proposals untouched

### F5: Indexes Created -- PASS

All 4 required indexes defined (lines 72-87) and created in `initialize()`:
- `idx_reports_generated_at`
- `idx_proposals_status`
- `idx_proposals_report_id`
- `idx_changes_applied_at`

Test `test_indexes_created` verifies all 4 exist in `sqlite_master`.

### F6: S4 Tests Still Pass (Path A) -- PASS

All 110 tests in `tests/intelligence/learning/` pass (27 new S3a + 83 existing S1/S2/S4). No production code was modified, so S4's ConfigProposalManager and its tests are unaffected.

## Schema Verification

All 3 required tables match the spec:
- `learning_reports`: report_id (PK), generated_at, analysis_window_start, analysis_window_end, report_json (TEXT), version (INT) -- MATCH
- `config_proposals`: proposal_id (PK), report_id (FK), field_path, current_value, proposed_value, rationale, status, created_at, updated_at, human_notes, applied_at, reverted_at -- MATCH
- `config_change_history`: change_id (PK AUTOINCREMENT), proposal_id (FK), field_path, old_value, new_value, source, applied_at, report_id -- MATCH

## Method Verification

All required methods present:
- **Report:** `save_report`, `get_report`, `list_reports`, `enforce_retention` -- all present
- **Proposal:** `save_proposal`, `update_proposal_status`, `list_proposals`, `get_pending_proposals`, `supersede_proposals` -- all present
- **Bonus:** `get_approved_proposals` (not in spec but used by S4's ConfigProposalManager) -- present and tested
- **Change history:** `record_change`, `get_change_history`, `get_latest_change` -- all present

Minor note: `record_change()` parameter order differs from spec (`field_path` first, `proposal_id` as optional keyword). This is a reasonable adaptation since `proposal_id` and `report_id` are nullable in the schema, and S4's ConfigProposalManager already uses this interface successfully.

## Test Quality Assessment

27 tests covering:
- WAL mode verification (1)
- Report CRUD: save, get, missing, list ordering/limit, date filter, empty DB (6)
- Proposal CRUD: save/list, filters, get_pending, get_approved (4)
- Status transitions: approved, applied_at, reverted_at, full state machine, dismissed/rejected (5)
- Supersession: pending from prior reports, no pending edge case (2)
- Change history: record/get, date filter, latest change, missing field (4)
- Retention: basic delete, APPLIED protection, REVERTED protection, empty DB (4)
- Index verification (1)
- Fire-and-forget error handling (1)

Coverage is thorough and exceeds the minimum of 10 tests.

## Escalation Criteria Check

| Criterion | Status |
|-----------|--------|
| ConfigProposalManager writes invalid YAML | N/A (no config writes in S3a) |
| Config application causes scoring regression | N/A (no config application in S3a) |
| Auto trigger blocks/delays shutdown | N/A (no auto trigger in S3a) |
| Mathematically impossible results | N/A (no analysis in S3a) |
| LearningStore fails to persist | NOT TRIGGERED -- all persistence tests pass |
| Config change history gaps | NOT TRIGGERED -- change history tested |

## Regression Checklist (Session-Relevant Items)

- [x] LearningStore creates data/learning.db without affecting other DBs
- [x] data/learning.db uses WAL mode
- [x] Report retention enforcement only deletes from learning.db
- [x] All 110 learning tests pass
- [x] No test hangs

## Findings

No findings. The session delivered exactly what was specified: comprehensive tests for S4's existing LearningStore implementation. Path A was the correct choice -- S4's code meets all requirements, and the 27 new tests provide thorough coverage of the persistence layer.

## Missing Artifact

No close-out report (`session-3a-closeout.md`) was found. The review proceeded based on the implementation prompt, the diff (single new test file), and direct code inspection.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "session": "Sprint 28, Session 3a",
  "reviewer": "Tier 2 Automated Review",
  "date": "2026-03-28",
  "tests_pass": true,
  "test_count": {
    "session_new": 27,
    "module_total": 110,
    "all_pass": true
  },
  "findings": [],
  "escalation_triggers": [],
  "notes": "Path A taken -- S4 learning_store.py adopted as-is. 27 new tests provide thorough coverage of all DEC-345 patterns, Amendment 6 supersession, Amendment 11 retention protection, and full proposal state machine. No production code modified. No close-out report found on disk (session-3a-closeout.md missing)."
}
```
