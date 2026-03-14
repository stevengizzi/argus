# Tier 2 Review: Sprint 24.1, Session 1a

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ` ```json:structured-verdict `. See the review skill for the
full schema and requirements.

**Write the review report to a file:**
`docs/sprints/sprint-24.1/session-1a-review.md`

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not
modify any files."

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-24.1/review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-24.1/session-1a-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1` (or the commit range for Session 1a)
- Test command (scoped — non-final session):
  ```
  python -m pytest tests/execution/test_order_manager*.py tests/analytics/test_trade_logger.py tests/db/ -x -q
  ```
- Files that should NOT have been modified:
  - `argus/core/events.py`
  - `argus/strategies/*`
  - `argus/api/routes/trades.py`
  - `argus/core/risk_manager.py`
  - `argus/intelligence/*`

## Session-Specific Review Focus
1. **Schema migration safety:** Verify ALTER TABLE ADD COLUMN statements are wrapped in try/except (or equivalent) and are idempotent. Running the migration twice must not fail.
2. **ManagedPosition backward compatibility:** Verify new fields have defaults so existing code that constructs ManagedPosition without quality data still works.
3. **Trade model backward compatibility:** Verify new fields have defaults. `model_post_init()` must not reference quality fields.
4. **TradeLogger NULL handling:** Verify `_row_to_trade()` handles NULL values from pre-sprint rows (quality_grade and quality_score not present in old rows).
5. **TradeLogger INSERT completeness:** Verify the INSERT column count matches the VALUES placeholder count (common off-by-one when adding columns).
6. **Order Manager passthrough only:** Verify quality fields are only stored and passed through — no logic branches on quality data in Order Manager.
7. **Signal field access:** Verify `_handle_entry_fill()` reads `signal.quality_grade` and `signal.quality_score` (not inventing values).
8. **Test coverage:** Verify tests cover: quality-present round-trip, quality-absent round-trip, NULL from legacy rows, schema migration idempotency.

## Additional Context
This session wires quality data through 4 files along a single chain: schema → Trade model → ManagedPosition → TradeLogger. The API routes (`api/routes/trades.py`) and frontend Trade type already have quality fields — they were pre-wired in Sprint 24 but the backend persistence was missing.
