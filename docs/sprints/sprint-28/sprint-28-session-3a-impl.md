# Sprint 28, Session 3a: LearningStore (SQLite Persistence)

## Pre-Flight Checks
1. Read: `argus/intelligence/learning/models.py` (S1), `argus/intelligence/counterfactual_store.py` (DEC-345 pattern reference)
2. Run: `python -m pytest tests/intelligence/learning/ -x -q` (S1+S2 tests passing)
3. Verify correct branch

## Objective
Build SQLite persistence layer for learning reports, config proposals, and config change history. Follows DEC-345 pattern (separate `data/learning.db`).

## Requirements

1. **Create `argus/intelligence/learning/learning_store.py`:**
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

## Constraints
- Do NOT modify any existing files
- Do NOT create or modify any DB other than `data/learning.db`
- Follow DEC-345 pattern exactly (WAL mode, fire-and-forget, rate-limited warnings)

## Test Targets
- `test_learning_store.py`: report CRUD, proposal CRUD, status transitions (full state machine per Amendment 6), supersession logic, change history recording, retention enforcement (basic + Amendment 11 protection), WAL mode verification, empty DB queries
- Minimum: 10 new tests
- Test command: `python -m pytest tests/intelligence/learning/ -x -q`

## Definition of Done
- [ ] LearningStore with 3 tables, WAL mode, fire-and-forget writes
- [ ] Proposal state machine: PENDING → APPROVED/DISMISSED/SUPERSEDED/REJECTED_GUARD/REJECTED_VALIDATION → APPLIED → REVERTED
- [ ] Retention enforcement protects APPLIED/REVERTED-referenced reports (Amendment 11)
- [ ] Supersession logic auto-expires prior PENDING proposals (Amendment 6)
- [ ] ≥10 new tests
- [ ] Close-out to `docs/sprints/sprint-28/session-3a-closeout.md`
- [ ] @reviewer with review context

## Session-Specific Review Focus (for @reviewer)
1. Verify DEC-345 pattern: WAL mode, fire-and-forget, rate-limited warnings
2. Verify proposal state machine matches Amendment 6 exactly
3. Verify retention enforcement skips APPLIED/REVERTED-referenced reports (Amendment 11)
4. Verify supersession only affects PENDING proposals from prior (not current) reports
5. Verify indexes are created

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*
