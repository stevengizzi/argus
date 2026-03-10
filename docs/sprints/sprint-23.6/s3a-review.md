# Tier 2 Review: Sprint 23.6, Session 3a

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session. Do NOT modify any files.
Follow the review skill in .claude/skills/review.md.
Your review report MUST include a structured JSON verdict at the end, fenced with ```json:structured-verdict.

## Review Context
Read `sprint-23.6/review-context.md` for Sprint Spec, Spec by Contradiction, regression checklist, and escalation criteria.

## Tier 1 Close-Out Report
---BEGIN-CLOSE-OUT---

**Session:** Sprint 23.6 — Session 3a: Intelligence Startup Factory
**Date:** 2026-03-10
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/intelligence/startup.py | added | New factory module for creating intelligence pipeline components |
| tests/intelligence/test_startup.py | added | Test suite for the startup factory (8 tests) |

### Judgment Calls
Decisions made during implementation that were NOT specified in the prompt:
- Used `# type: ignore[arg-type]` for ai_client/usage_tracker params: The classifier and briefing generator constructors expect non-None types, but we need to support None for fallback mode. The runtime handling is correct (classifier checks client.enabled internally).

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Create `argus/intelligence/startup.py` | DONE | startup.py created |
| `IntelligenceComponents` dataclass | DONE | startup.py:35-49 |
| `create_intelligence_components` factory | DONE | startup.py:52-128 |
| Return None when disabled | DONE | startup.py:70-72 |
| Create storage with `{data_dir}/catalyst.db` path | DONE | startup.py:75-76 |
| Build sources list based on enabled flags | DONE | startup.py:79-90 |
| Create classifier (handles disabled ai_client) | DONE | startup.py:93-105 |
| Create briefing_generator | DONE | startup.py:108-113 |
| Create pipeline | DONE | startup.py:116-122 |
| Log what was created | DONE | startup.py:124-129 |
| `shutdown_intelligence` helper | DONE | startup.py:132-145 |
| 8+ new tests | DONE | test_startup.py (8 tests) |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| No existing files modified | PASS | `git status` shows only new files |
| Existing intelligence tests pass | PASS | 104 existing + 8 new = 112 total passing |

### Test Results
- Tests run: 112
- Tests passed: 112
- Tests failed: 0
- New tests added: 8
- Command used: `python -m pytest tests/intelligence/ -x -q`

### Unfinished Work
None

### Notes for Reviewer
None

---END-CLOSE-OUT---

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/intelligence/test_startup.py -x -q`
- Files that should NOT have been modified: anything except `argus/intelligence/startup.py` and test files

## Session-Specific Review Focus
1. Verify factory returns None (not empty components) when disabled
2. Verify each source is only instantiated when its individual `enabled` flag is True
3. Verify classifier handles both ai_client=None and ai_client.enabled=False
4. Verify shutdown helper calls both pipeline.stop() AND storage.close()
5. Verify no import of SystemConfig — factory takes CatalystConfig, not the full system config
6. Verify TYPE_CHECKING guards for ClaudeClient, UsageTracker, EventBus (avoid circular imports)
