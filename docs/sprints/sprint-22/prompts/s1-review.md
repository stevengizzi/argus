# Tier 2 Review: Sprint 22, Session 1 — AI Core Module

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    docs/sprints/sprint-22/prompts/review-context.md

## Tier 1 Close-Out Report

[PASTE SESSION 1 CLOSE-OUT REPORT HERE]

## Review Scope
- Diff: `git diff main..HEAD -- argus/ai/ argus/core/config.py`
- New files expected: `argus/ai/{__init__.py, client.py, prompts.py, context.py, cache.py, config.py, tools.py}`
- Modified files expected: `argus/core/config.py` (AIConfig addition)
- Files that should NOT have been modified: `argus/strategies/`, `argus/execution/`, `argus/data/`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/core/event_bus.py`, any existing API routes
- Test command: `python -m pytest tests/ai/ -x -q`

## Session-Specific Review Focus
1. Verify ClaudeClient does NOT make API calls at import time or in constructor
2. Verify system prompt template contains all required sections: ARGUS description, strategy summaries, behavioral guardrails ("never recommend entries/exits", "caveat uncertainty", "reference actual data")
3. Verify 5 tool definitions match DEC-272 enumeration exactly
4. Verify TOOLS_REQUIRING_APPROVAL excludes generate_report
5. Verify AIConfig defaults are sane (token budgets match DEC-273)
6. Verify config backward compatibility — parse config without `ai:` section
7. Verify token budget enforcement in PromptManager history truncation
8. Check: `anthropic` import is lazy or graceful when package not installed

## Additional Context
- Implementation prompt for this session: `docs/sprints/sprint-22/prompts/s1-impl.md`
