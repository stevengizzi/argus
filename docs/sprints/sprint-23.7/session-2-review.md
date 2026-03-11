# Tier 2 Review: Sprint 23.7, Session 2

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

`sprint-23.7/review-context.md`

## Tier 1 Close-Out Report
[PASTE THE SESSION 2 CLOSE-OUT REPORT HERE]

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/ -x -q`
- Files that should NOT have been modified: strategy files, orchestrator,
  risk manager, order manager, frontend code, AI layer, intelligence pipeline,
  databento_data_service.py (Session 1 scope)

## Session-Specific Review Focus
1. Verify periodic cache saves use atomic writes (temp file + rename), not
   direct writes that could corrupt on kill
2. Verify the 1,000-symbol checkpoint interval is based on successful fetches,
   not total attempts (failed symbols should not inflate the counter)
3. Verify the incremental fetch logic respects partially cached data — a
   cache with 15,000 symbols should result in ~22,000 incremental fetches,
   not 37,000
4. Verify the shutdown signal handler actually triggers during an active
   fetch (not just during idle)
5. Verify the API server double-bind root cause is documented in the
   close-out report
6. Verify the port-availability guard uses a proper socket check, not just
   a try/except around uvicorn.run()
7. Verify the port guard does not introduce a TOCTOU race (time-of-check
   vs time-of-use) — acceptable as defense-in-depth since the root cause
   is also fixed, but note if present
8. Verify the cache JSON schema is unchanged (backward compatible with
   existing cache files)

## Additional Context
This session addresses two independent bugs. Part A (cache saves) prevents
data loss on interrupted cold-starts (previously required re-doing a 2-hour
fetch). Part B (API double-bind) prevents a boot crash observed when
restarting ARGUS rapidly. The reviewer should treat these as independent
changes that happen to be in the same session for efficiency.