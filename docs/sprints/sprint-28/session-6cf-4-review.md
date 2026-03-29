---BEGIN-REVIEW---

# Tier 2 Review — Sprint 28, Session S6cf-4 (Final Polish)

**Reviewer:** Automated Tier 2
**Date:** 2026-03-29
**Commit range:** Uncommitted changes on main (working tree)
**Close-out report:** `docs/sprints/sprint-28/session-6cf-4-closeout.md`

## Summary

Three targeted polish fixes: (1) removed 4 redundant `@field_validator` methods from `LearningLoopConfig`, (2) added `closed_position_count` property to `CounterfactualTracker` and updated `main.py` to use it, (3) added a test for the learning-disabled config path.

## Review Focus Verification

### 1. All 8 TestLearningLoopConfig tests pass with only Field(ge=,le=) constraints

**VERIFIED.** Ran `pytest tests/intelligence/learning/test_models.py::TestLearningLoopConfig -v` -- 8 tests passed (the close-out says 6 in scope verification but the test class has 8 tests total; all pass). Pydantic v2 `Field(ge=, le=)` constraints produce error messages that include the field name in the `loc` tuple, so all existing `match=` patterns continue to match.

### 2. closed_position_count property returns int, not list

**VERIFIED.** Line 402 of `counterfactual.py`: `return len(self._closed_positions)` -- returns `int`. Return type annotation is `-> int`.

### 3. main.py getattr default is 0 (int), not [] (list)

**VERIFIED.** Line 1606 of `main.py`: `getattr(self._counterfactual_tracker, "closed_position_count", 0)` -- default is `0` (int), matching the property return type.

### 4. Disabled-path test triggers server lifespan

**VERIFIED.** The test constructs `AppState` without learning components (default `None`), creates the app via `create_app(app_state)`, and makes a request via `AsyncClient`. The server lifespan in `server.py` checks `config.learning_loop.enabled` -- when `False`, it logs "Learning Loop disabled" and does not initialize learning components. The test then asserts `learning_service`, `learning_store`, and `config_proposal_manager` remain `None`. Test passes.

### 5. Ruff check -- zero NEW warnings

**VERIFIED.** Ran `ruff check` on all three modified source files. All 16 warnings reported are pre-existing (line length violations, import sorting, SIM102 nested-if suggestions in `main.py`; unused imports and SIM105 in `counterfactual.py`). Zero new warnings introduced by the session's changes.

## Change-by-Change Analysis

### Fix 1: models.py -- Remove redundant validators

- 4 `@field_validator` methods deleted (lines 404-438 in the original)
- `field_validator` removed from Pydantic import
- Deletion-only change. No new code introduced.
- Correct: the `Field(ge=, le=)` constraints on lines 390-402 already enforce identical bounds.

### Fix 2: counterfactual.py -- Add closed_position_count property

- 4-line property added after `get_closed_positions()` at line 399
- Returns `len(self._closed_positions)` as `int`
- Matches the constraint of "one property addition (4 lines)"
- No other changes to the file.

### Fix 3: main.py -- Replace private attribute access

- 3-line net change: replaced `getattr(tracker, "_closed_positions", [])` + `len()` with `getattr(tracker, "closed_position_count", 0)`
- Public API access instead of private attribute access. Default `0` is type-safe.
- No other changes to the file.

### Fix 4: test_learning_api.py -- New disabled-path test

- Test uses the same construction pattern as the existing `learning_app_state` fixture (full AppState with all required fields).
- Close-out notes a judgment call: the implementation prompt's suggested test code had incorrect constructor signatures for `HealthMonitor` and `FixedClock`, and omitted required `AppState` fields. The session adapted appropriately to match existing fixture patterns.
- Test is standalone (no fixture dependency), which is appropriate since it tests a different config path.

## Constraint Compliance

| Constraint | Status |
|-----------|--------|
| No strategy/risk/orchestrator files modified | PASS |
| No config files modified | PASS |
| counterfactual.py limited to one property (4 lines) | PASS |
| main.py limited to getattr change (3 lines net) | PASS |
| models.py deletion only | PASS |
| All existing tests pass | PASS (141 learning, 15 API) |

## Test Results

- `TestLearningLoopConfig`: 8/8 passed
- `test_learning_disabled_components_are_none`: PASSED
- All 141 learning tests: PASSED
- Ruff: 0 new warnings

## Findings

No issues found. All three fixes are minimal, correct, and match the spec precisely. The judgment call on the test fixture construction was appropriate and well-documented.

## Verdict: CLEAR

All review focus items verified. Changes are deletion-only or minimal additions, all within spec constraints. Tests pass. No regressions.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "summary": "Three targeted polish fixes implemented correctly: redundant Pydantic validators removed, private attribute access replaced with public property, disabled-path test added. All 8 validation tests pass without custom validators, property returns correct type, getattr default matches, new test triggers lifespan. Zero new ruff warnings. No issues found.",
  "findings": [],
  "tests_passed": true,
  "tests_total": 141,
  "tests_added": 1,
  "ruff_clean": true,
  "ruff_new_warnings": 0
}
```
