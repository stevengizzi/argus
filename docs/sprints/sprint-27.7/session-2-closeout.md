---BEGIN-CLOSE-OUT---

**Session:** Sprint 27.7 S2 — CounterfactualStore + Config Layer
**Date:** 2026-03-25
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/intelligence/counterfactual_store.py` | added | SQLite persistence for counterfactual positions |
| `config/counterfactual.yaml` | added | Default configuration for Counterfactual Engine |
| `argus/intelligence/config.py` | modified | Added CounterfactualConfig Pydantic model |
| `argus/core/config.py` | modified | Wired counterfactual field onto SystemConfig |
| `tests/intelligence/test_counterfactual_store.py` | added | 12 tests covering store CRUD, retention, config validation |

### Judgment Calls
- None. All decisions were pre-specified in the implementation prompt.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| CounterfactualStore with aiosqlite, WAL, table + indexes | DONE | `counterfactual_store.py:initialize()` |
| write_open() — INSERT on position open | DONE | `counterfactual_store.py:write_open()` |
| write_close() — UPDATE exit fields | DONE | `counterfactual_store.py:write_close()` |
| query() — flexible filters | DONE | `counterfactual_store.py:query()` |
| get_closed_positions() — convenience method | DONE | `counterfactual_store.py:get_closed_positions()` |
| enforce_retention() — DELETE old records | DONE | `counterfactual_store.py:enforce_retention()` |
| count() — total record count | DONE | `counterfactual_store.py:count()` |
| Fire-and-forget writes with rate-limited warnings | DONE | `counterfactual_store.py:_warn()` |
| config/counterfactual.yaml | DONE | `config/counterfactual.yaml` |
| CounterfactualConfig Pydantic model | DONE | `intelligence/config.py:CounterfactualConfig` |
| SystemConfig.counterfactual field | DONE | `core/config.py:SystemConfig` |
| Config validation test (YAML↔Pydantic) | DONE | `test_counterfactual_store.py:test_config_yaml_keys_match_pydantic_fields` |
| ≥8 new tests | DONE | 12 new tests |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| CounterfactualStore uses `data/counterfactual.db` | PASS | Default db_path in `__init__` |
| SystemConfig defaults still work | PASS | `SystemConfig()` constructs; full suite passes |
| CounterfactualConfig field names match YAML keys | PASS | Test 8 explicitly verifies exact match |
| No changes to main.py or startup.py | PASS | `git diff` shows no changes |

### Test Results
- Tests run: 3,448 (full suite) / 36 (scoped)
- Tests passed: 3,448 / 36
- Tests failed: 0
- New tests added: 12
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`

### Unfinished Work
- None. All spec items are complete.

### Notes for Reviewer
- Store uses `data/counterfactual.db` (separate DB per DEC-345 pattern), not `argus.db`.
- WAL mode enabled in `initialize()`.
- Retention enforcement deletes by `opened_at` date only.
- Fire-and-forget `_warn()` helper rate-limits to 1 warning per 60 seconds via `time.monotonic()`.
- `get_closed_positions()` uses `closed_at IS NOT NULL` filter plus date range and optional keyword filters.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27.7",
  "session": "S2",
  "verdict": "COMPLETE",
  "tests": {
    "before": 3436,
    "after": 3448,
    "new": 12,
    "all_pass": true
  },
  "files_created": [
    "argus/intelligence/counterfactual_store.py",
    "config/counterfactual.yaml",
    "tests/intelligence/test_counterfactual_store.py"
  ],
  "files_modified": [
    "argus/intelligence/config.py",
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
  "implementation_notes": "Straightforward implementation following EvaluationEventStore pattern. 12 tests (4 over minimum). Store, config, and wiring all match spec exactly."
}
```
