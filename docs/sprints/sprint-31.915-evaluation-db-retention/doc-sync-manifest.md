# Sprint 31.915 Doc-Sync Manifest

> Mid-sprint manifest per `protocols/mid-sprint-doc-sync.md`. Required
> because the session files 5 new DEFs (DEF-231 through DEF-235) and 1
> new DEC (DEC-389), changing CLAUDE.md DEF-table state and decision-log
> state mid-flight.

## Triggering event

Sprint 31.915 Session 1 close-out files 5 new DEFs and 1 new DEC. CLAUDE.md
DEF-table receives 4 strikethrough RESOLVED-IN-SPRINT rows
(DEF-231/232/233/234) and 1 OPEN-DEFERRED row (DEF-235). The decision-log
gains DEC-389 with rationale + cross-refs to DEF-234 + IMPROMPTU-10's
DEF-197 closure.

## Files touched

| File | Change shape | Sprint-close transition owed |
|---|---|---|
| `CLAUDE.md` | DEF table: append 5 rows (DEF-231/232/233/234 strikethrough RESOLVED-IN-SPRINT, DEF-235 OPEN-DEFERRED); Current State pytest count update; recent-sprints note | DEF-231/232/233/234 strikethrough verified at sprint close; DEF-235 routing confirmed |
| `docs/decision-log.md` | Append DEC-389 entry | DEC-389 present, well-formed, cross-refs to DEF-234 + DEF-197 |
| `docs/dec-index.md` | Append DEC-389 line; update header count from 388 → 389 | Header count = 389; DEC-389 present in body |
| `docs/sprint-history.md` | Append Sprint 31.915 row with anchor commit | Row present with anchor commit |
| `docs/sprints/sprint-31.915-evaluation-db-retention/session-1-closeout.md` | New file (close-out) | File present + structured JSON appendix |
| `docs/sprints/sprint-31.915-evaluation-db-retention/session-1-review.md` | New file (Tier 2 review verdict) | File present + structured JSON verdict |
| `docs/operations/evaluation-db-runbook.md` | New file (operator runbook) | File present, 2 pages, references DEF-232/235 |
| `dev-logs/2026-04-28_retention-mechanism-diagnostic.md` | New file (Phase A findings) | File present, contains raw evidence + mechanism analysis |

## Code/config files (out-of-scope for doc-sync but listed for completeness)

| File | Change shape |
|---|---|
| `argus/core/config.py` | Add `EvaluationStoreConfig` Pydantic model + `SystemConfig.evaluation_store` field + register `("evaluation_store", "evaluation_store.yaml")` in `_STANDALONE_SYSTEM_OVERLAYS` |
| `argus/strategies/telemetry_store.py` | Config-driven retention + observability fixes (G1/G3/G4/G5) |
| `argus/main.py` | Wire `config.system.evaluation_store` into `EvaluationEventStore.__init__` + `register_evaluation_store(self._eval_store)` on HealthMonitor |
| `argus/api/server.py` | Same config wiring for the alternate init path; same `register_evaluation_store` call |
| `argus/core/health.py` | Add `register_evaluation_store()` + `get_evaluation_db_health()` methods; add `_evaluation_store` instance attribute |
| `argus/api/routes/health.py` | Add `EvaluationDbHealth` Pydantic model; extend `HealthResponse`; render via `state.health_monitor.get_evaluation_db_health()` |
| `config/evaluation_store.yaml` | New file (operator-facing config surface, bare-field shape per DEC-384) |
| `tests/test_telemetry_store.py` | Append 8 new tests + 1-line surgical adaptation to existing IMPROMPTU-10 test |
| `tests/api/test_health.py` | Append 2 new tests |

## What does NOT change

- `argus/data/migrations/evaluation.py` and any migration framework code.
- The 5 Sprint 31.8 VACUUM tests in
  `tests/strategies/test_telemetry_store_vacuum.py`.
- The 3 IMPROMPTU-10 lifecycle tests in `tests/test_telemetry_store.py`
  (except the surgical 1-line monkeypatch adaptation called out in
  Judgment Calls).
- `argus/intelligence/counterfactual_store.py`,
  `argus/intelligence/experiments/store.py`,
  `argus/intelligence/learning/learning_store.py`,
  `argus/data/vix_data_service.py`, `argus/intelligence/storage.py`,
  `argus/core/regime_history.py`, `argus/api/routes/alerts.py`.
- `workflow/` submodule.
