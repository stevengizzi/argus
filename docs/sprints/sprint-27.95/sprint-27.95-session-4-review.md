# Tier 2 Review: Sprint 27.95, Session 4

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict.

**Write the review report to:**
`docs/sprints/sprint-27.95/session-4-review.md`

## Review Context
`docs/sprints/sprint-27.95/review-context.md`

## Tier 1 Close-Out Report
`docs/sprints/sprint-27.95/session-4-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/execution/ tests/test_main* -x -q`
- Files that should NOT have been modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/intelligence/`, `argus/data/`

## Session-Specific Review Focus
1. Verify flatten happens BEFORE market data streaming starts
2. Verify flatten uses broker abstraction (not raw IBKR calls)
3. Verify known ARGUS positions are never touched by startup cleanup
4. Verify portfolio query failure is handled gracefully (no crash)
5. CRITICAL: If startup flatten could close positions that should be kept → ESCALATE

## Additional Context
March 26 showed 8 zombie RECO positions (BTU, ADPT, ZURA, QID, YOU, VNDA, INDV, VERA) reconstructed at boot with 0 shares, $0 entry, no stop. These persisted indefinitely. The fix auto-flattens unknown positions (default enabled) instead of creating unmanageable RECO entries.
