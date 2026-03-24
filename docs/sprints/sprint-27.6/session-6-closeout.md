```markdown
---BEGIN-CLOSE-OUT---

**Session:** Sprint 27.6 S6 — Integration: V2 Compose + Orchestrator + main.py + RegimeHistoryStore
**Date:** 2026-03-24
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/core/regime.py | modified | Added `run_pre_market()` async method to RegimeClassifierV2; updated `compute_regime_vector()` to query actual calculator snapshot methods instead of Protocol.compute(); changed constructor types from Protocol to concrete calculator types; added logging import |
| argus/core/regime_history.py | added | New RegimeHistoryStore class with SQLite persistence, fire-and-forget write, 7-day retention, query by date/timestamp/summary |
| argus/core/events.py | modified | Added `regime_vector_summary: dict[str, Any] | None = None` field to RegimeChangeEvent |
| argus/core/orchestrator.py | modified | Accept `regime_classifier_v2` and `regime_history` in constructor; compute RegimeVector after V1 classify in both `reclassify_regime()` and `run_pre_market()`; enrich RegimeChangeEvent with vector summary; fire-and-forget write to history store |
| argus/main.py | modified | Phase 8.5: config-gated creation of BreadthCalculator, MarketCorrelationTracker, SectorRotationAnalyzer, IntradayCharacterDetector, RegimeClassifierV2, RegimeHistoryStore; V2 pre-market call before Orchestrator pre-market; async wrapper Event Bus subscriptions for breadth + intraday calculators |
| tests/core/test_regime_integration.py | added | 10 integration tests: V2 compose (full/none/disabled), V1 delegation, config-gate, Orchestrator reclassify with V2, RegimeChangeEvent enrichment, pre-market concurrent execution, Event Bus subscriptions for breadth and intraday |
| tests/core/test_regime_history.py | added | 7 history store tests: write+query by date, query by timestamp, fire-and-forget failure, 7-day retention, summary, config-gate persist_history, regime_vector_json stored |

### Judgment Calls
- Used async wrapper functions for BreadthCalculator.on_candle and IntradayCharacterDetector.on_candle Event Bus subscriptions since EventBus requires async handlers but the calculators have sync on_candle methods.
- Read orchestrator config twice (once for V2 creation in Phase 8.5, once in Phase 9) since V2 needs it before Orchestrator construction. Minimal perf impact (YAML file read is cached).
- Used `object | None` type for `_latest_regime_vector` on Orchestrator to avoid circular import between orchestrator.py and regime.py (RegimeVector).

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| V2 compute_regime_vector queries each calculator snapshot | DONE | regime.py:compute_regime_vector — uses get_breadth_snapshot/get_correlation_snapshot/get_sector_snapshot/get_intraday_snapshot |
| V2 run_pre_market with asyncio.gather | DONE | regime.py:run_pre_market — gathers correlation.compute + sector.fetch |
| V2 regime_confidence uses real data from calculators | DONE | regime.py:_compute_regime_confidence — counts enabled dimensions with data |
| RegimeHistoryStore with write/query/retention | DONE | regime_history.py — full CRUD + 7-day retention on initialize |
| RegimeChangeEvent.regime_vector_summary optional | DONE | events.py — `dict[str, Any] | None = None` |
| Orchestrator accepts V2 + history | DONE | orchestrator.py constructor |
| Orchestrator reclassify with V2 | DONE | orchestrator.py:reclassify_regime + run_pre_market |
| Orchestrator enriches event with vector summary | DONE | orchestrator.py:_run_regime_recheck + run_pre_market |
| Orchestrator fire-and-forget write | DONE | orchestrator.py uses asyncio.create_task for history.record |
| main.py config-gate | DONE | Phase 8.5: `if regime_config.enabled` |
| main.py calculator creation | DONE | Phase 8.5: all 4 calculators + V2 + history store |
| main.py Event Bus subscriptions | DONE | Phase 10.5: async wrappers for breadth + intraday |
| main.py pre-market V2 call | DONE | Between Phase 9 Orchestrator start and run_pre_market |
| Config-gate absolute: enabled=false → zero V2 code | DONE | All V2 creation gated on regime_config.enabled |
| 14+ tests | DONE | 17 tests (10 integration + 7 history) |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Existing core tests (477) | PASS | 494 total (477 + 17 new) |
| Full backend suite | PASS | 3,283 passed, 0 failed |
| RegimeChangeEvent backward compat | PASS | regime_vector_summary defaults to None |
| V1-only path (no V2) | PASS | Orchestrator with V2=None unchanged |
| evaluation.py not modified | PASS | Constraint respected |
| comparison.py not modified | PASS | Constraint respected |
| ensemble_evaluation.py not modified | PASS | Constraint respected |
| databento_data_service.py not modified | PASS | Constraint respected |
| strategies/*.py not modified | PASS | Constraint respected |

### Test Results
- Tests run: 3,283
- Tests passed: 3,283
- Tests failed: 0
- New tests added: 17
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`

### Unfinished Work
None

### Notes for Reviewer
- The V2 constructor now takes concrete types (BreadthCalcImpl, MarketCorrelationTracker, etc.) instead of Protocol types. The Protocol types remain in regime.py but are no longer used by V2 — they can be cleaned up in a future session.
- The Orchestrator stores `_latest_regime_vector` as `object | None` to avoid importing RegimeVector (which would create a potential circular import). The `hasattr(obj, "to_dict")` check provides safe duck-typing.
- The `orchestrator_yaml` is loaded twice (Phase 8.5 + Phase 9) because V2 needs the config before Orchestrator construction. Both loads produce the same config from the same YAML file.

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27.6",
  "session": "S6",
  "verdict": "COMPLETE",
  "tests": {
    "before": 3266,
    "after": 3283,
    "new": 17,
    "all_pass": true
  },
  "files_created": [
    "argus/core/regime_history.py",
    "tests/core/test_regime_integration.py",
    "tests/core/test_regime_history.py"
  ],
  "files_modified": [
    "argus/core/regime.py",
    "argus/core/events.py",
    "argus/core/orchestrator.py",
    "argus/main.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "Protocol types (BreadthCalculator, CorrelationCalculator, SectorRotationCalculator, IntradayCalculator) in regime.py are no longer used by V2 — can be cleaned up or kept for future alternative implementations",
    "orchestrator_yaml loaded twice (Phase 8.5 + Phase 9) — could be DRY'd but minimal perf impact"
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "V2 constructor switched from Protocol types to concrete calculator types to enable direct snapshot queries. EventBus subscriptions for sync on_candle methods require async wrapper functions. Orchestrator stores _latest_regime_vector as object|None to avoid circular import."
}
```
