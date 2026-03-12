# Tier 2 Review: Sprint 23.8, Session 3

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
- Diff to review: `git diff HEAD~1` (or the appropriate range for Session 3 commits)
- Test command: `python -m pytest tests/intelligence/sources/ tests/data/test_databento*.py -x -q`
- Files that should NOT have been modified: `startup.py`, `pipeline.py`, `server.py`, `classifier.py`, `storage.py`, `core/`, `strategies/`, `execution/`, `ui/`, `ai/`

## Session-Specific Review Focus
1. Verify all three source files use `ClientTimeout(total=30, sock_connect=10, sock_read=20)` — check that `sock_connect` and `sock_read` are explicit keyword arguments, not positional
2. Verify the FMP circuit breaker resets at the START of each `fetch_catalysts()` call — not in `__init__` or `start()`, which would only reset once
3. Verify the FMP circuit breaker activates on HTTP 403 specifically — not on all HTTP errors (a 500 or timeout should NOT trigger the circuit breaker, those are transient)
4. Verify the circuit breaker logs ERROR on the first 403 and WARNING with a skip count at cycle end — not the other way around
5. Verify the Databento `end` clamp uses `timedelta(seconds=600)` — not minutes, not a magic number without a comment referencing DEC-326
6. Verify the clamp ONLY applies to the mid-session lazy warm-up path — check that the pre-market boot path (DEC-316 skip) is completely unmodified
7. Verify that when clamped `end < start`, the warm-up is skipped gracefully (not errored) with a DEBUG-level log
8. Verify no changes to the Databento live streaming connection or the ALL_SYMBOLS subscription
9. Verify source rate limit configurations are unchanged — `sec_edgar.rate_limit_per_second`, `finnhub.rate_limit_per_minute` should be untouched
10. Verify no source fetch logic was changed — the same endpoints are called with the same parameters, only timeout and error handling changed

## Additional Context
The timeout changes address a real hang observed during QA: the polling loop entered and never produced output. The `asyncio.wait_for(120)` added in Session 1 is the safety net; the `sock_connect`/`sock_read` timeouts in this session are the precision fix. Together they provide defense-in-depth — individual requests timeout at 30s max, and the entire gather times out at 120s if something unexpected happens.

The FMP circuit breaker addresses 100+ wasted 403 requests observed in the QA log. The FMP news source is currently disabled in `system_live.yaml` (Starter plan doesn't include news endpoints), but the circuit breaker should work correctly for when/if the plan is upgraded.

The Databento warm-up fix addresses ~15 consecutive 422 errors observed during a mid-session boot. The historical API lags ~10 minutes behind the live stream. The 600s buffer is conservative. If Databento reduces their lag in the future, the buffer just means warm-up data ends a few minutes earlier — not a correctness issue, just slightly less warm-up data.
