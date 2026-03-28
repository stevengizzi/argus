# Sprint 28, Session 3a: LearningStore (SQLite Persistence) — UPDATED

> **This prompt supersedes the original `sprint-28-session-3a-impl.md`.** It incorporates carry-forward context from Session 4, which created `learning_store.py` as an S4 dependency.

## Carry-Forward Context (Critical — Read First)

**S4 already created `argus/intelligence/learning/learning_store.py`.** Session 4 (ConfigProposalManager) needed LearningStore as a dependency and built a full implementation. The S4 Tier 2 review flagged this as a MEDIUM finding (F-1) — documented judgment call, functionally correct.

**Your first task** is to read S4's `learning_store.py` and diff it against this session's requirements below. Then take one of two paths:

- **Path A (Adopt + Extend):** If S4's implementation covers the schema, WAL mode, fire-and-forget pattern, and most methods, adopt it as-is and add any missing methods, retention enforcement (Amendment 11), and supersession logic (Amendment 6). This is the expected path — S4's close-out confirms 3 tables, WAL mode, DEC-345 pattern.
- **Path B (Replace):** If S4's implementation is structurally incompatible with the requirements below, replace it entirely. Document the incompatibility in your close-out.

**Either way, the Definition of Done below is the authoritative checklist.** S4's implementation is a head start, not a substitute for verification.

## Pre-Flight Checks
1. Read: `argus/intelligence/learning/learning_store.py` (**existing from S4** — diff against requirements below)
2. Read: `argus/intelligence/learning/models.py` (S1), `argus/intelligence/counterfactual_store.py` (DEC-345 pattern reference)
3. Run: `python -m pytest tests/intelligence/learning/ -x -q` (S1+S2+S4 tests passing — expect 83)
4. Verify correct branch

## Objective
Ensure the SQLite persistence layer for learning reports, config proposals, and config change history is complete and fully tested. Follows DEC-345 pattern (separate `data/learning.db`).

## Requirements

**These are the authoritative requirements. Verify each against S4's existing implementation.**

1. **`argus/intelligence/learning/learning_store.py`:**
   - `LearningStore` class with async init (creates `data/learning.db`, WAL mode)
   - **Schema — 3 tables:**
     - `learning_reports`: report_id (PK), generated_at, analysis_window_start, analysis_window_end, report_json (TEXT — serialized LearningReport), version (INT)
     - `config_proposals`: proposal_id (PK), report_id (FK), field_path, current_value, proposed_value, rationale, status, created_at, updated_at, human_notes, applied_at, reverted_at
     - `config_change_history`: change_id (PK), proposal_id (FK), field_path, old_value, new_value, source (TEXT — "learning_loop" or "revert"), applied_at, report_id
   - **Report methods:** `save_report(report)`, `get_report(report_id)`, `list_reports(start_date, end_date, limit)`, `enforce_retention(retention_days)` — **Amendment 11:** skip reports referenced by APPLIED/REVERTED proposals
   - **Proposal methods:** `save_proposal(proposal)`, `update_proposal_status(proposal_id, status, notes)`, `list_proposals(status_filter, report_id_filter)`, `get_pending_proposals()`, `supersede_proposals(report_id)` — sets all PENDING proposals from prior reports to SUPERSEDED (Amendment 6)
   - **Change history methods:** `record_change(proposal_id, field_path, old_value, new_value, source)`, `get_change_history(start_date, end_date)`, `get_latest_change(field_path)` — for revert lookup
   - Fire-and-forget writes with rate-limited warnings (DEC-345 pattern)
   - Indexes: `idx_reports_generated_at`, `idx_proposals_status`, `idx_proposals_report_id`, `idx_changes_applied_at`

2. **If S4's implementation is adopted:** Focus your time on:
   - Verifying every method signature and schema column matches the requirements above
   - Adding any missing methods (especially `enforce_retention` with A11 protection, `supersede_proposals` with A6 logic, `get_latest_change`)
   - Writing comprehensive tests (the primary deliverable for this session if S4's code is already solid)
   - Fixing any gaps found during verification

3. **`__init__.py` exports:** Verify `LearningStore` and `ConfigProposalManager` are both exported (S4 may have already done this).

## Constraints
- Do NOT modify any files outside `argus/intelligence/learning/` and `tests/intelligence/learning/`
- Do NOT create or modify any DB other than `data/learning.db`
- Follow DEC-345 pattern exactly (WAL mode, fire-and-forget, rate-limited warnings)
- S4's `config_proposal_manager.py` and its tests are NOT in scope for modification — those are S4's deliverables

## Test Targets
- `tests/intelligence/learning/test_learning_store.py`: report CRUD, proposal CRUD, status transitions (full state machine per Amendment 6), supersession logic, change history recording, retention enforcement (basic + Amendment 11 protection), WAL mode verification, empty DB queries
- Minimum: 10 new tests
- Test command: `python -m pytest tests/intelligence/learning/ -x -q`

## Definition of Done
- [ ] LearningStore with 3 tables, WAL mode, fire-and-forget writes — **all methods from Requirements §1 present and functional**
- [ ] Proposal state machine: PENDING → APPROVED/DISMISSED/SUPERSEDED/REJECTED_GUARD/REJECTED_VALIDATION → APPLIED → REVERTED
- [ ] Retention enforcement protects APPLIED/REVERTED-referenced reports (Amendment 11)
- [ ] Supersession logic auto-expires prior PENDING proposals (Amendment 6)
- [ ] All S4 tests still pass (83 expected)
- [ ] ≥10 new tests in `test_learning_store.py`
- [ ] Close-out report documents whether Path A or Path B was taken and why
- [ ] @reviewer with review context

## Session-Specific Review Focus (for @reviewer)
1. Verify DEC-345 pattern: WAL mode, fire-and-forget, rate-limited warnings
2. Verify proposal state machine matches Amendment 6 exactly
3. Verify retention enforcement skips APPLIED/REVERTED-referenced reports (Amendment 11)
4. Verify supersession only affects PENDING proposals from prior (not current) reports
5. Verify indexes are created
6. **NEW:** If Path A taken, verify S4's existing implementation was not degraded — S4 tests must still pass
7. **NEW:** If Path B taken, verify S4's `config_proposal_manager.py` still works with the replacement (import compatibility)

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*