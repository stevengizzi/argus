# Tier 2 Review: Sprint 27.7, Session 2

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict.

**Write the review report to a file:**
`docs/sprints/sprint-27.7/session-2-review.md`

## Review Context
`docs/sprints/sprint-27.7/review-context.md`

## Tier 1 Close-Out Report
`docs/sprints/sprint-27.7/session-2-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/intelligence/test_counterfactual_store.py tests/intelligence/test_counterfactual.py tests/core/test_fill_model.py -x -q`
- Files that should NOT have been modified: `argus/main.py`, `argus/intelligence/startup.py`, `argus/core/events.py`, any files in `argus/strategies/`, any files in `argus/ui/`, `config/system.yaml`, `config/system_live.yaml`

## Session-Specific Review Focus
1. Verify store uses `data/counterfactual.db` — separate file, not argus.db
2. Verify WAL mode is enabled on the store connection
3. Verify retention enforcement deletes only by `opened_at` date, not other criteria
4. Verify CounterfactualConfig Pydantic field names match YAML keys exactly
5. Verify `SystemConfig.counterfactual` has `Field(default_factory=CounterfactualConfig)` — not a bare default
6. Verify fire-and-forget write pattern includes warning-level logging with rate limiting

## Additional Context
Session 2 of 6. Builds persistence and config layer. The highest-risk area is the Pydantic config wiring — field names must match YAML keys exactly or values silently use defaults.
