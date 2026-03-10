# Tier 2 Review: Sprint 23.6, Session 3b

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session. Do NOT modify any files.
Follow the review skill in .claude/skills/review.md.
Your review report MUST include a structured JSON verdict at the end, fenced with ```json:structured-verdict.

## Review Context
Read `sprint-23.6/review-context.md`.

## Tier 1 Close-Out Report
[PASTE THE CLOSE-OUT REPORT HERE AFTER THE IMPLEMENTATION SESSION]

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/api/ tests/core/test_config.py -x -q`
- Files that should NOT have been modified: `argus/strategies/`, `argus/execution/`, `argus/ai/`, `argus/ui/`, `argus/analytics/`, `argus/backtest/`, `argus/intelligence/` (except startup.py if needed), `argus/data/`

## Session-Specific Review Focus
1. Verify `catalyst: CatalystConfig` added to SystemConfig with `Field(default_factory=CatalystConfig)`
2. Verify intelligence initialization block in lifespan follows the SAME pattern as AI services (conditional, try/except, cleanup)
3. Verify `components` variable persists across yield for shutdown access
4. Verify `pipeline.start()` is called (sources need to be started)
5. Verify shutdown calls `shutdown_intelligence(components)` — not just nulling AppState fields
6. Verify the existing AI services block is UNCHANGED (diff should show additions only in that area)
7. Verify config YAML key validation test exists (no silently ignored Pydantic fields)
8. Verify intelligence init happens AFTER AI services init (so ai_client is available)
