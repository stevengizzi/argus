```markdown
---BEGIN-CLOSE-OUT---

**Session:** Sprint 27.6 S9 — Operating Conditions Matching
**Date:** 2026-03-24
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/core/regime.py | modified | Added RegimeOperatingConditions dataclass and matches_conditions() method on RegimeVector |
| argus/core/config.py | modified | Added operating_conditions field to StrategyConfig, imported RegimeOperatingConditions |
| tests/core/test_operating_conditions.py | added | 16 tests covering construction, range matching, string matching, None handling, AND logic, YAML parsing |

### Judgment Calls
None

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| RegimeOperatingConditions dataclass with float ranges and string lists | DONE | argus/core/regime.py:RegimeOperatingConditions |
| RegimeVector.matches_conditions() with AND logic | DONE | argus/core/regime.py:RegimeVector.matches_conditions() |
| None constraint = unconstrained (always matches) | DONE | matches_conditions() skips None constraints |
| None RegimeVector field with non-None constraint = non-matching | DONE | matches_conditions() returns False for None field values |
| Empty conditions = vacuously true | DONE | matches_conditions() returns True when all constraints None |
| StrategyConfig operating_conditions field | DONE | argus/core/config.py:StrategyConfig.operating_conditions |
| Backward compat (missing operating_conditions → None) | DONE | Field defaults to None |
| No strategy wiring | DONE | No strategy files modified |
| 8+ tests | DONE | 16 tests in tests/core/test_operating_conditions.py |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Existing regime tests pass | PASS | 88 tests in test_regime.py + models unchanged |
| No strategy files modified | PASS | Only regime.py and config.py touched |
| Full test suite passes | PASS | 3,307 passed, 0 failed |
| StrategyConfig backward compat | PASS | Existing configs parse without operating_conditions |

### Test Results
- Tests run: 3,307
- Tests passed: 3,307
- Tests failed: 0
- New tests added: 16
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`

### Unfinished Work
None

### Notes for Reviewer
- RegimeOperatingConditions is a frozen dataclass (not Pydantic), consistent with RegimeVector pattern
- Pydantic v2 handles frozen dataclass coercion from dict natively (YAML list → tuple works)
- matches_conditions() uses table-driven approach with explicit range_checks and string_checks lists for maintainability
- No circular import: regime.py imports config.py only under TYPE_CHECKING; config.py imports regime.py at runtime

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27.6",
  "session": "S9",
  "verdict": "COMPLETE",
  "tests": {
    "before": 3291,
    "after": 3307,
    "new": 16,
    "all_pass": true
  },
  "files_created": [
    "tests/core/test_operating_conditions.py"
  ],
  "files_modified": [
    "argus/core/regime.py",
    "argus/core/config.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "RegimeOperatingConditions uses frozen dataclass pattern consistent with RegimeVector. Pydantic v2 coerces dict/list inputs to dataclass fields natively, so YAML parsing works without custom validators."
}
```
