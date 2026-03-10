# Tier 2 Review: Sprint 23.6, Session 3b

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session. Do NOT modify any files.
Follow the review skill in .claude/skills/review.md.
Your review report MUST include a structured JSON verdict at the end, fenced with ```json:structured-verdict.

## Review Context
Read `sprint-23.6/review-context.md`.

## Tier 1 Close-Out Report
---BEGIN-CLOSE-OUT---

**Session:** Sprint 23.6 S3b — App Lifecycle Wiring (Static)
**Date:** 2026-03-10
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/core/config.py | modified | Added CatalystConfig import and catalyst field to SystemConfig |
| argus/api/server.py | modified | Added intelligence initialization and shutdown in lifespan handler |
| tests/api/test_server_intelligence.py | added | 9 tests for intelligence lifespan integration |

### Judgment Calls
None

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| SystemConfig.catalyst field exists | DONE | config.py:183-184 |
| Intelligence components created in lifespan when enabled | DONE | server.py:123-153 |
| AppState.catalyst_storage and briefing_generator populated | DONE | server.py:139-141 |
| Cleanup runs on shutdown | DONE | server.py:178-190 |
| Config YAML keys match Pydantic model | DONE | test_config_catalyst_yaml_keys_match_model |
| All existing tests pass | DONE | 2432 existing tests pass |
| 8+ new tests written and passing | DONE | 9 new tests passing |
| No ruff lint errors | DONE | All checks passed |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Config loading works | PASS | catalyst.enabled = False as expected |
| Existing server tests pass | PASS | 379 API tests passed |
| No changes to protected files | PASS | Empty diff for strategies/execution/analytics/backtest/ui |
| AI services init unchanged | PASS | Verified in git diff — AI block untouched |

### Test Results
- Tests run: 2441
- Tests passed: 2441
- Tests failed: 0
- New tests added: 9
- Command used: `python -m pytest tests/ -x -q`

### Unfinished Work
None

### Notes for Reviewer
None

---END-CLOSE-OUT---

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
