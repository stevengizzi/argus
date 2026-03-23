# Tier 2 Review: Sprint 25.9, Session 2

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):
`docs/sprints/sprint-25.9/session-2-review.md`

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not
modify any files" — the review report file is the sole permitted write.

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-25.9/sprint-25.9-review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-25.9/session-2-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command (final session, full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Files that should NOT have been modified: anything in `argus/strategies/`, `argus/execution/`, `argus/analytics/`, `argus/ai/`, `argus/intelligence/`, `argus/ui/`, `argus/backtest/`, `argus/core/orchestrator.py`

## Session-Specific Review Focus
1. Verify checkpoint merge logic is `existing ∪ fresh` with fresh taking precedence — not the other way around, not additive without dedup
2. Verify the existing cache is loaded into memory at START of fetch cycle, not re-read at each checkpoint
3. Verify `trust_cache_on_startup=false` fully reverts to the pre-sprint blocking behavior
4. Verify background refresh task is properly registered for shutdown cancellation
5. Verify routing table rebuild is a single-assignment swap, not a mutation of the existing table
6. Verify no new `await` calls were added to the startup synchronous path when trust=true
7. Verify the cache file path hasn't changed (still `data/reference_cache.json`)
8. Verify the FMP rate limiting is respected during background refresh (batching, delays between batches)

## Additional Context
This is Session 2 of an impromptu sprint. Session 1 fixed regime filtering and logging. This session fixes the data-destructive cache checkpoint bug (B1) and implements trust-cache-on-startup (B2/DEF-063). The B1 fix is a correctness fix for a confirmed data loss bug. The B2 fix restructures the startup sequence so that cached reference data is used immediately, with stale entries refreshed in the background. The key risk is the startup sequence change — Phase 7.5 behavior changes from "block until fresh" to "use cached, refresh later."
