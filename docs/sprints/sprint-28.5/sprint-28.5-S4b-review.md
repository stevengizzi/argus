# Tier 2 Review: Sprint 28.5, Session S4b

## Instructions
READ-ONLY review. Follow `.claude/skills/review.md`.
Write report to: `docs/sprints/sprint-28.5/session-S4b-review.md`

## Review Context
Read: `docs/sprints/sprint-28.5/review-context.md`

## Tier 1 Close-Out Report
Read: `docs/sprints/sprint-28.5/session-S4b-closeout.md`

## Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/unit/execution/test_order_manager_exit_management.py tests/unit/execution/test_order_manager.py -x -q -v`
- Files NOT modified: fill_model.py, risk_manager.py, on_approved bracket submission

## Session-Specific Review Focus

**SAFETY-CRITICAL SESSION — All AMD checks are mandatory:**

1. **CRITICAL AMD-2:** Verify `_trail_flatten` submits market sell BEFORE cancelling broker safety stop. This is the #1 safety requirement. The exact order must be: (1) check _flatten_pending, (2) add to _flatten_pending, (3) submit sell, (4) cancel safety stop.
2. **CRITICAL AMD-8:** Verify `_flatten_pending` check is the absolute FIRST thing in both `_trail_flatten` and escalation update paths — before ANY broker calls (no cancels, no submits, no state changes if pending).
3. **AMD-3:** Verify escalation stop resubmission failure triggers `_flatten_position`, not silent failure.
4. **AMD-4:** Verify `shares_remaining > 0` guard prevents sell of 0 shares in both trail and escalation paths.
5. **AMD-6:** Verify escalation path does NOT increment `_stop_retry_count`.
6. Verify non-trail positions (exit_config=None or trailing_stop.enabled=False) have ZERO behavioral change — all existing Order Manager tests must pass unchanged.
7. Verify trail stop only ratchets up (monotonically non-decreasing).
8. Verify T2 check still works alongside trail (both coexist in on_tick).
9. Verify `activation: "after_profit_pct"` only activates trail after threshold exceeded.

## Additional Context
This is the core Order Manager state machine change. The 5 safety-critical amendments (AMD-2/3/4/6/8) are the primary review focus. Every existing Order Manager test must pass with zero changes.
