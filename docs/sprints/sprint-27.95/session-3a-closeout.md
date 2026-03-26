---BEGIN-CLOSE-OUT---

**Session:** Sprint 27.95 — Session 3a: Overflow Infrastructure
**Date:** 2026-03-26
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/intelligence/counterfactual.py` | modified | Added `BROKER_OVERFLOW = "broker_overflow"` to `RejectionStage` enum |
| `argus/intelligence/config.py` | modified | Added `OverflowConfig` Pydantic model + `Field` import |
| `argus/core/config.py` | modified | Wired `OverflowConfig` into `SystemConfig` with `default_factory` |
| `config/overflow.yaml` | added | Reference/template YAML for overflow configuration |
| `config/system.yaml` | modified | Added inline `overflow:` section (enabled: true, broker_capacity: 30) |
| `config/system_live.yaml` | modified | Added inline `overflow:` section (enabled: true, broker_capacity: 30) |
| `tests/intelligence/test_counterfactual.py` | modified | Added `BROKER_OVERFLOW` assertion to existing test + new dedicated test |
| `tests/intelligence/test_config.py` | modified | Added 4 new `OverflowConfig` tests (defaults, validation, YAML alignment) |

### Judgment Calls
- Placed `OverflowConfig` in `argus/intelligence/config.py` alongside `CounterfactualConfig` rather than in `argus/core/config.py`: overflow is part of the intelligence/signal pipeline, and the prompt says to follow the `CounterfactualConfig` pattern which lives in `intelligence/config.py`.
- Note: The prompt references `RejectionStage` as being in `argus/core/events.py`, but it is actually defined in `argus/intelligence/counterfactual.py`. The events.py file only references it in a comment on `SignalRejectedEvent.rejection_stage`. Implemented in the actual location.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Add `BROKER_OVERFLOW = "broker_overflow"` to `RejectionStage` enum | DONE | `argus/intelligence/counterfactual.py:41` |
| Create `config/overflow.yaml` | DONE | `config/overflow.yaml` |
| Add `OverflowConfig(BaseModel)` with `enabled` and `broker_capacity` fields | DONE | `argus/intelligence/config.py:OverflowConfig` |
| Wire into SystemConfig (follow CounterfactualConfig pattern) | DONE | `argus/core/config.py:SystemConfig.overflow` |
| Add overflow section to `system.yaml` | DONE | `config/system.yaml` |
| Add overflow section to `system_live.yaml` | DONE | `config/system_live.yaml` |
| 6+ new tests | DONE | 6 new tests (2 enum + 4 config) |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Existing RejectionStage values unchanged | PASS | QUALITY_FILTER, POSITION_SIZER, RISK_MANAGER, SHADOW all still present |
| No behavioral changes to signal pipeline | PASS | No imports of OverflowConfig outside config layer |
| Config loading for existing sections unaffected | PASS | 619 tests pass including all config tests |

### Test Results
- Tests run: 619
- Tests passed: 619
- Tests failed: 0
- New tests added: 6
- Command used: `python -m pytest tests/core/ tests/intelligence/test_config.py tests/intelligence/test_counterfactual.py -x -q`

### Unfinished Work
None

### Notes for Reviewer
- `RejectionStage` lives in `argus/intelligence/counterfactual.py`, not in `argus/core/events.py` as the impl prompt stated. The enum was modified in its actual location.
- `OverflowConfig.broker_capacity` uses `Field(default=30, ge=0)` for the `>= 0` validator per spec.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27.95",
  "session": "S3a",
  "verdict": "COMPLETE",
  "tests": {
    "before": 599,
    "after": 619,
    "new": 6,
    "all_pass": true
  },
  "files_created": [
    "config/overflow.yaml",
    "docs/sprints/sprint-27.95/session-3a-closeout.md"
  ],
  "files_modified": [
    "argus/intelligence/counterfactual.py",
    "argus/intelligence/config.py",
    "argus/core/config.py",
    "config/system.yaml",
    "config/system_live.yaml",
    "tests/intelligence/test_counterfactual.py",
    "tests/intelligence/test_config.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "RejectionStage enum is in argus/intelligence/counterfactual.py, not events.py as the impl prompt stated. OverflowConfig placed in intelligence/config.py alongside CounterfactualConfig to follow the established pattern."
}
```
