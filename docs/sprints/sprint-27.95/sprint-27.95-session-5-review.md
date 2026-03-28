# Tier 2 Review: Sprint 27.95, Session 5 — Carry-Forward Cleanup

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file:**
docs/sprints/sprint-27.95/session-5-review.md

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

docs/sprints/sprint-27.95/review-context.md

## Tier 1 Close-Out Report
Read the close-out report from:
docs/sprints/sprint-27.95/session-5-closeout.md

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/execution/ tests/core/test_config.py -x -q`
- Files that should NOT have been modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/ai/`, `argus/data/`, `argus/analytics/evaluation.py`

## Session-Specific Review Focus
1. Verify the zero-qty guard fires BEFORE `_flatten_unknown_position()` is called, not after
2. Verify normal (non-reconciliation) close path uses direct `position.original_stop_price` access — no `getattr`
3. Verify reconciliation close path still uses `getattr` with fallback
4. Verify `_resubmit_stop_with_retry` references `stop_cancel_retry_max`, NOT `stop_retry_max`
5. Verify `_submit_stop_order` still references `stop_retry_max` (unchanged)
6. Verify both YAML files have the new `stop_cancel_retry_max` field

## Sprint-Level Regression Checklist
| Check | Expected |
|-------|----------|
| Normal position lifecycle unchanged | All existing position lifecycle tests pass |
| Reconciliation redesign (S1a) intact | `test_order_manager_reconciliation_redesign.py` passes |
| Trade logger fix (S1b) intact | `test_trade_logger_reconciliation.py` passes |
| Order mgmt hardening (S2) intact | `test_order_manager_hardening.py` passes |
| Startup zombie cleanup (S4) intact | S4 tests in `test_order_manager.py` pass |
| Overflow routing (S3b) intact | `test_overflow_routing.py` passes |
| Overflow → counterfactual (S3c) intact | `test_counterfactual_overflow.py` passes |
| Full test suite passes, no hangs | All scoped tests pass |

## Sprint-Level Escalation Criteria
1. Any change breaks position lifecycle tests
2. Any change breaks the reconciliation redesign from Session 1a
3. Stop resubmission cap (Session 2) no longer triggers emergency flatten at correct threshold
4. Startup flatten closes positions that should be kept
5. Test hang (>10 minutes)

## Additional Context
This is a cleanup session addressing three carry-forward issues from Sprint 27.95 review findings (F-002, F-004, and the shared stop_retry_max config). All three fixes are in files already modified this sprint (order_manager.py, config.py, YAML files). No new architectural surface area. This is the final session before sprint close-out and doc-sync.
