# Tier 2 Review: Sprint 27, Session 2

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict.

**Write the review report to a file:**
docs/sprints/sprint-27/session-2-review.md

## Review Context
Read: docs/sprints/sprint-27/review-context.md

## Tier 1 Close-Out Report
Read: docs/sprints/sprint-27/session-2-closeout.md

## Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/backtest/test_historical_data_feed.py -x -q`
- Do-not-modify: `argus/backtest/data_fetcher.py`, `argus/data/databento_utils.py`, `argus/core/`, `argus/strategies/`

## Session-Specific Review Focus
1. Verify cost validation is fail-closed: get_cost() exception → halt download (AR-3)
2. Verify verify_zero_cost=False completely skips cost check
3. Verify Parquet cache path: `{cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet`
4. Verify normalize_databento_df() imported from argus.data.databento_utils (not reimplemented)
5. Verify Databento client is lazy-created (not at __init__ or import time)
6. Verify no live API calls in tests
