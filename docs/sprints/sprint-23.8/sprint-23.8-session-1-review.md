# Tier 2 Review: Sprint 23.8, Session 1

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-23.8-review-context.md`

## Tier 1 Close-Out Report
[PASTE THE CLOSE-OUT REPORT HERE AFTER THE IMPLEMENTATION SESSION]

## Review Scope
- Diff to review: `git diff HEAD~1` (or the appropriate range for Session 1 commits)
- Test command: `python -m pytest tests/ -x -q`
- Files that should NOT have been modified: `core/`, `strategies/`, `execution/`, `ui/`, `ai/` (except `server.py`), `backtest/`, `classifier.py`, source files (`sec_edgar.py`, `finnhub.py`, `fmp_news.py`), `databento_data_service.py`

## Session-Specific Review Focus
1. Verify `asyncio.wait_for()` wraps the gather with a 120s timeout — not the entire poll loop iteration, just the gather call
2. Verify `asyncio.TimeoutError` is caught correctly and does NOT crash the loop — it must log CRITICAL and continue to the next sleep/poll cycle
3. Verify `get_symbols()` prioritizes scanner watchlist over viable universe — check the fallback order is: watchlist → capped viable → empty list
4. Verify the `max_batch_size` cap is applied when falling back to viable universe — hard-coding a cap instead of reading config is a CONCERN
5. Verify `done_callback` logs at CRITICAL level (not WARNING or ERROR) when the task raises an exception
6. Verify task reference is stored on `app_state` (not a local variable) to prevent garbage collection
7. Verify the QA session debug patches were replaced, not layered — search for any remaining temporary diagnostic code
8. Verify the config alignment test fix is correct — the test should validate `system_live.yaml` including the catalyst section, not skip it
9. Verify no changes were made to polling interval logic or market-hours awareness

## Additional Context
This session replaces temporary debug patches added during a live QA session on March 12, 2026. The debug patches (a `done_callback` and a "Polling loop coroutine entered" log) confirmed the task was alive but hanging. Those patches were intentionally quick-and-dirty — this session should replace them with production-quality implementations.

The `get_symbols()` change is architecturally significant: it determines what the intelligence pipeline monitors. The QA session proved that passing the full viable universe (6,342 symbols) causes the poll to timeout. The fix scopes to the scanner watchlist (15 symbols). A future Sprint 24 design decision (DEC-327) will revisit this with a firehose architecture. For now, the watchlist is the correct scope.
