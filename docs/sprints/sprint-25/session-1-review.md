---BEGIN-REVIEW---

# Sprint 25, Session 1 — Tier 2 Review Report

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-17
**Diff:** `git diff HEAD~1` (commit d3e2fd1)
**Session Self-Assessment:** MINOR_DEVIATIONS

---

## 1. Spec Conformance

| Spec Requirement | Status | Notes |
|-----------------|--------|-------|
| ObservatoryService with 4 query methods | PASS | `get_pipeline_stages`, `get_closest_misses`, `get_symbol_journey`, `get_session_summary` |
| 7 pipeline tiers in get_pipeline_stages | PASS | universe, viable, routed, evaluating, near_trigger, signal, traded |
| Closest misses sorted by conditions_passed desc | PASS | Verified in tests and code |
| Symbol journey chronological | PASS | ORDER BY timestamp ASC |
| Session summary with top blockers + closest miss | PASS | Implemented with aggregation queries |
| 4 REST endpoints, JWT-protected | PASS | All endpoints use `Depends(require_auth)` |
| ObservatoryConfig Pydantic model | PASS | 5 fields matching review-context table |
| Config-gated: disabled = no routes | PASS | Tested: returns 404 when disabled |
| Wire into SystemConfig | PASS | core/config.py: `observatory: ObservatoryConfig` |
| YAML config sections | PASS | Both system.yaml and system_live.yaml |
| 15+ new tests | PASS | 28 tests (21 service + 7 route) |
| Date defaults to today (ET) | PASS | `_today_et()` uses `ZoneInfo("America/New_York")` |
| No Event Bus subscribers | PASS | Grep confirms zero subscribe calls |
| Backward compatible without YAML section | PASS | `Field(default_factory=ObservatoryConfig)` |

## 2. Boundary Compliance

| Boundary | Status | Notes |
|----------|--------|-------|
| No modifications to argus/strategies/ | PASS | |
| No modifications to argus/core/orchestrator.py | PASS | |
| No modifications to argus/core/risk_manager.py | PASS | |
| No modifications to argus/execution/ | PASS | |
| No modifications to argus/intelligence/quality_engine.py | PASS | |
| No modifications to argus/intelligence/position_sizer.py | PASS | |
| No modifications to argus/data/ | PASS | |
| No modifications to argus/ai/ | PASS | |
| No modifications to existing page components | PASS | |
| No new Event Bus subscribers | PASS | |
| No evaluation telemetry schema changes | PASS | |
| argus/core/config.py modification | ACCEPTABLE | Minimal: 1 import + 2 lines for SystemConfig field. Config infrastructure, not trading pipeline. Spec explicitly requires this. |

## 3. Session-Specific Focus Items

### 3a. ObservatoryService reads from EvaluationEventStore and UniverseManager without modifying them

PASS. The service is purely read-only:
- EvaluationEventStore: only SELECT queries against `evaluation_events` table.
- UniverseManager: reads via public properties (`reference_cache`, `viable_count`) and public method (`get_universe_stats()`). No mutations.

### 3b. No Event Bus subscribers added

PASS. Grep of all new files confirms zero `subscribe` or `add_subscriber` calls.

### 3c. Condition detail parsing handles missing fields gracefully

PASS. `_extract_conditions()` handles three metadata formats plus empty metadata. `_safe_json_loads()` handles None, empty string, invalid JSON, and non-dict JSON. Tests cover all these cases.

### 3d. Date parameter defaults to today (ET timezone)

PASS. `_today_et()` uses `datetime.now(ZoneInfo("America/New_York"))` correctly.

### 3e. ObservatoryConfig follows CatalystConfig/QualityEngineConfig pattern

PASS. Same pattern: Pydantic BaseModel with Field defaults, imported into core/config.py, wired into SystemConfig with `Field(default_factory=...)`.

### 3f. Config-gating: endpoints not mounted when observatory.enabled = false

PASS. Server.py checks `config.observatory.enabled` before both initializing ObservatoryService and mounting the router. Test `test_observatory_disabled_no_routes` verifies 404 response.

## 4. Findings

### F-001 [LOW] Private attribute access on EvaluationEventStore._conn

`ObservatoryService` accesses `self._store._conn` directly (lines 91, 161, 268 of observatory_service.py). This couples the service to the internal implementation of EvaluationEventStore. The store does not expose `_conn` via a public property. This is functional but fragile -- if EvaluationEventStore refactors its connection handling, ObservatoryService breaks.

**Recommendation:** Add a public property or query method to EvaluationEventStore in a future session, rather than reaching into private state.

### F-002 [LOW] datetime.utcnow() usage in observatory routes

Line 151 of `argus/api/routes/observatory.py` uses `datetime.utcnow()`, which is deprecated in Python 3.12+ (and the project's own decision log DEC-003 already addressed this project-wide). Should use `datetime.now(UTC)` instead.

**Impact:** Cosmetic only -- this is for response timestamp generation, not time-sensitive trading logic. The project is on Python 3.11 where `utcnow()` still works, but inconsistent with the project standard.

### F-003 [LOW] ConditionDetail uses `object | None` type annotation

`ConditionDetail` Pydantic model (lines 50-51 of observatory.py) uses `object | None` for `actual_value` and `required_value`. While functional, `object` is very broad. Using `float | str | bool | None` or `Any` (with explicit import) would be more precise. This is a minor typing concern -- the fields are for display only and values vary by condition type.

### F-004 [INFO] "traded" tier uses QUALITY_SCORED as proxy

The close-out report documents this judgment call. QUALITY_SCORED is indeed in `EvaluationEventType` and is emitted by all 4 strategies after quality scoring. This is a reasonable proxy since it is the last telemetry event before order placement. The approximation is that a QUALITY_SCORED event does not guarantee an order was placed (the quality grade might be below minimum), so the "traded" count may slightly overcount. This is documented and acceptable for visualization purposes.

### F-005 [INFO] Symbol journey query fetches `reason` column (index 4) but does not include it in the response dict

The SQL in `get_symbol_journey()` selects `reason` as column 4 but the list comprehension skips from `row[3]` (result) to `row[5]` (metadata_json), omitting `reason`. The `JourneyEvent` Pydantic model also has no `reason` field. This appears intentional (reason is redundant with metadata), but slightly wasteful -- the column could be dropped from the SELECT.

## 5. Regression Check

| Check | Result |
|-------|--------|
| Session-specific tests | 28/28 PASS |
| API + analytics + config tests | 600/600 PASS |
| No forbidden files modified | PASS |
| No Event Bus subscribers added | PASS |
| Config backward-compatible | PASS |
| Existing API tests unaffected | PASS |

## 6. Escalation Criteria Evaluation

| Criterion | Triggered? | Notes |
|-----------|-----------|-------|
| Three.js < 30fps | N/A | No Three.js code in this session |
| Bundle size > 500KB increase | N/A | No frontend code in this session |
| Observatory WS degrades Copilot WS | N/A | No WebSocket code in this session |
| Any trading pipeline modification required | NO | Read-only service, config wiring only |
| Non-Observatory page load > 100ms increase | N/A | No frontend code in this session |

No escalation criteria triggered.

## 7. Verdict

**CONCERNS**

The implementation is solid, complete, and well-tested. All spec requirements are met. All boundary constraints are respected. The three LOW findings (private attribute access on `_conn`, deprecated `datetime.utcnow()`, broad `object` type) are individually minor but worth documenting for future cleanup. None of these block progress to Session 2.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "25",
  "session": "S1",
  "verdict": "CONCERNS",
  "findings_count": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 3,
    "info": 2
  },
  "escalation_triggered": false,
  "tests_pass": true,
  "test_count_verified": true,
  "boundary_violations": [],
  "findings": [
    {
      "id": "F-001",
      "severity": "LOW",
      "category": "coupling",
      "summary": "Private attribute access on EvaluationEventStore._conn",
      "file": "argus/analytics/observatory_service.py",
      "lines": [91, 161, 268]
    },
    {
      "id": "F-002",
      "severity": "LOW",
      "category": "code-style",
      "summary": "datetime.utcnow() usage; should be datetime.now(UTC) per DEC-003",
      "file": "argus/api/routes/observatory.py",
      "lines": [151]
    },
    {
      "id": "F-003",
      "severity": "LOW",
      "category": "typing",
      "summary": "ConditionDetail uses `object | None` for actual_value/required_value",
      "file": "argus/api/routes/observatory.py",
      "lines": [50, 51]
    },
    {
      "id": "F-004",
      "severity": "INFO",
      "category": "design",
      "summary": "traded tier uses QUALITY_SCORED as proxy -- may slightly overcount"
    },
    {
      "id": "F-005",
      "severity": "INFO",
      "category": "efficiency",
      "summary": "Symbol journey SQL selects reason column but does not include it in response"
    }
  ],
  "recommendation": "Proceed to Session 2. Low findings can be addressed in a polish pass."
}
```
