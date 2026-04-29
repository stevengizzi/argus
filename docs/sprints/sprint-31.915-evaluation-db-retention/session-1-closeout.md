# Sprint 31.915 — Session 1 Closeout

**Sprint:** 31.915 — `evaluation.db` Retention Mechanism + Observability
**Session:** 1 (single-session impromptu, full-protocol)
**Date:** 2026-04-28 → 2026-04-29
**Pre-session SHA:** `84d072b`
**Post-session SHA:** `e58edec`
**CI:** TBD (operator runs after review CLEAR)

---

## Summary

Single-session impromptu sprint resolving 4 coupled `data/evaluation.db`
concerns surfaced during the Apr 28 disk-pressure investigation:
silent-failure mode in IMPROMPTU-10's periodic retention task,
operator-disk-incompatible default `RETENTION_DAYS = 7`, missing
operational visibility on `/health`, and the chicken-and-egg disk
pressure trap that VACUUM creates under tight disk environments.

Phase A diagnostic conclusively ruled out the prompt's primary
hypothesis (H1, aiosqlite `cursor.rowcount` post-commit) and confirmed
H3 (vacuum-raises-eats-success-INFO). Phase B implemented the
config-driven retention policy via a new `EvaluationStoreConfig`
Pydantic model + `config/evaluation_store.yaml` standalone overlay,
plus the G1/G3/G4/G5 observability + safety fixes. Phase C added 10 new
regression tests, the operator runbook, and the doc-sync manifest.

DEC-389 written. DEF-231/232/233/234 RESOLVED-IN-SPRINT.
DEF-235 OPEN-DEFERRED (test-zombie FD-pin sibling-class to DEF-049).

---

## Phase A — Instrumented Diagnostic

`scripts/diag_retention_logging.py` (single-use; deleted post-Phase-A
per spec A4) reproduced the IMPROMPTU-10 retention path under
production-equivalent logger config. Three scenarios:

1. **outside_retention_window_minus_10d** — seed 100 rows 10 days outside
   the 7-day window. Result: `rowcount_before_commit = 100`,
   `rowcount_after_commit = 100`, 100 rows actually removed from disk,
   freelist 0 → 3 pages (10 page DB).
2. **inside_retention_window_plus_1d** — seed 100 rows inside retention;
   nothing should delete. Result: `rowcount = 0` both before and after
   commit; rows preserved.
3. **h3_probe_vacuum_raises** — seed rows outside window; force `_vacuum`
   to raise `OSError("ENOSPC: ...")`. Result: deletion-INFO never
   emitted; only generic `WARNING: periodic retention iteration failed`
   surfaces from `_run_periodic_retention`'s broad except.

**Findings written to** `dev-logs/2026-04-28_retention-mechanism-diagnostic.md`.

**Confirmed root cause:** H3 with mechanism refinement — the silent-failure
mode is not a single bug but an observability gap with two coupled
facets:
- The success-path INFO log line lived AFTER `await self._vacuum()`, so
  any vacuum failure ate the deletion record.
- The zero-deletion branch was completely silent, so during Apr 22–27
  (before any rows aged out) the periodic task ran ~36 times and emitted
  zero log lines per iteration.

**Halt-or-proceed gate:** H1 ruled out, H3 confirmed; no HALT required.
The spec's Phase B fix shape (G3/G4/G5 together) addresses every
plausible silent-failure path.

---

## Phase B — Implementation

### Files modified (10 total)

| File | Change shape |
|---|---|
| `argus/core/config.py` | Add `EvaluationStoreConfig` Pydantic model after `HealthConfig`; expose on `SystemConfig.evaluation_store` field; register `("evaluation_store", "evaluation_store.yaml")` in `_STANDALONE_SYSTEM_OVERLAYS` |
| `argus/strategies/telemetry_store.py` | (a) Add `config: EvaluationStoreConfig | None = None` parameter to `__init__`. (b) Sync config values into instance attributes (`self.RETENTION_DAYS = self._config.retention_days` etc.) for backward-compat with Sprint 31.8 VACUUM regression tests. (c) Move deletion-INFO emission BEFORE `await self._vacuum()` (G1 / G3 / DEF-231). (d) Add explicit zero-deletion INFO line. (e) Add `_last_retention_run_at_et` + `_last_retention_deleted_count` instance fields updated in both branches (G5 / DEF-233). (f) Add pre-VACUUM disk-headroom check in `_vacuum()` — non-bypassable per RULE-039 (G4 / DEF-232). (g) Add `get_health_snapshot()` + `get_freelist_pct()` helpers. |
| `argus/main.py` | Wire `config.system.evaluation_store` into `EvaluationEventStore.__init__`; call `self._health_monitor.register_evaluation_store(self._eval_store)` after construction. |
| `argus/api/server.py` | Same config wiring for the alternate init path; same `register_evaluation_store` call (gated on `app_state.health_monitor is not None`). |
| `argus/core/health.py` | Add `_evaluation_store: EvaluationEventStore | None = None` instance attribute; add `register_evaluation_store(store)` and `async get_evaluation_db_health()` methods returning all-null defaults when store is unregistered. |
| `argus/api/routes/health.py` | Add `EvaluationDbHealth` Pydantic model; extend `HealthResponse` with `evaluation_db: EvaluationDbHealth`; render via `await state.health_monitor.get_evaluation_db_health()`. |
| `config/evaluation_store.yaml` | New file. Bare-field shape per DEC-384/FIX-02 standalone-overlay convention. |
| `tests/test_telemetry_store.py` | Append 8 new tests (config-driven, both log branches, vacuum-raises sibling guard, headroom check both branches, snapshot fields) + 1-line surgical adaptation to existing IMPROMPTU-10 `test_periodic_retention_invokes_cleanup_old_events` (monkeypatch target migrated from class constant to instance attribute). Also add `import asyncio` and `from typing import Any` at file top for the new tests. |
| `tests/api/test_health.py` | Append 2 new tests — endpoint surfaces 4 `evaluation_db` keys both with no store registered (null defaults) and with a registered store (real values after retention). |

### Files NEW (4)

- `config/evaluation_store.yaml`
- `dev-logs/2026-04-28_retention-mechanism-diagnostic.md`
- `docs/operations/evaluation-db-runbook.md`
- `docs/sprints/sprint-31.915-evaluation-db-retention/doc-sync-manifest.md`
- `docs/sprints/sprint-31.915-evaluation-db-retention/session-1-closeout.md` (this file)

### Files NOT modified (per constraint list)

- `argus/data/migrations/evaluation.py` and any other file under `argus/data/migrations/`.
- `argus/intelligence/counterfactual_store.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/learning/learning_store.py`, `argus/data/vix_data_service.py`, `argus/intelligence/storage.py`, `argus/core/regime_history.py`, `argus/api/routes/alerts.py`.
- `tests/strategies/test_telemetry_store_vacuum.py` (Sprint 31.8 VACUUM regression suite).
- `workflow/` submodule.

---

## Judgment Calls

1. **Phase A confirmed H3, not H1 — fix shape adapted accordingly.**
   The sprint-spec assumed H1 (aiosqlite `cursor.rowcount` post-commit
   semantics) as the primary hypothesis and prescribed a 2-line fix
   (capture rowcount BEFORE `commit`). Phase A conclusively ruled this
   out: rowcount returns the correct deleted-row count BOTH before and
   after `commit()` on the in-tree aiosqlite version. The actual
   mechanism is H3 (vacuum-raises-eats-success-INFO) plus a coupled
   observability gap (zero-deletion branch silent). The spec author
   acknowledged this contingency: "If Phase A finds a different root
   cause, adapt the fix shape to match; the observability behavior is
   unchanged." The deviation: `cleanup_old_events()` emits the
   deletion-INFO line BEFORE `await self._vacuum()` rather than after,
   so a vacuum failure cannot eat the deletion record. The spec's
   prescribed Phase B fix shape kept `logger.info(...)` AFTER
   `await self._vacuum()`, which would still lose the INFO under H3.
   This deviation is the H3-correct fix; the observability behavior is
   strictly stronger than the spec's prescription.

2. **Class constants retained as DEPRECATED aliases for Sprint 31.8 VACUUM
   regression-test compat.** The Sprint 31.8 VACUUM regression tests at
   `tests/strategies/test_telemetry_store_vacuum.py` are on the
   "do NOT modify" list. They exercise startup-reclaim VACUUM logic by
   setting `store.STARTUP_RECLAIM_MIN_SIZE_MB = 0` and
   `store.STARTUP_RECLAIM_FREELIST_RATIO = 0.3` directly on the
   instance. After my initial refactor (production reads
   `self._config.startup_reclaim_min_size_mb` etc.), these tests broke
   because instance-attribute assignment had no effect on `_config`.
   Resolution: keep the legacy class-constant declarations
   (`RETENTION_DAYS: int = 2`, `STARTUP_RECLAIM_MIN_SIZE_MB: int = 500`,
   etc.) AS DEPRECATED ALIASES, sync them from `_config` in `__init__`
   (`self.RETENTION_DAYS = self._config.retention_days`), and have
   production code read `self.X` rather than `self._config.X`. This is
   exactly the spec's "Keep the class constants as DEPRECATED aliases
   that read from `_config` only if absolutely required" pattern,
   realized via instance-attribute sync rather than property
   descriptors. The `_config` Pydantic object remains the source of
   truth at construction time; runtime reads honor either path.
   Not a silent-default anti-pattern (RULE-042) because:
   - `__init__` ALWAYS syncs from config to instance.
   - Production reads `self.X` which always resolves (instance attr
     after sync).
   - There is NO `getattr(obj, "field", default)` fallback.

3. **IMPROMPTU-10 test surgical adaptation now targets the instance
   attribute, not `_config`.** The original test monkeypatches
   `EvaluationEventStore.RETENTION_INTERVAL_SECONDS` at the class level
   to 0.05. After my refactor, `__init__` syncs `self.X = self._config.X`
   at construction time, which would override the class-level
   monkeypatch. Spec said: change to `store._config.retention_interval_seconds = ...`.
   But production reads `self.RETENTION_INTERVAL_SECONDS` (instance
   attr), not `self._config.retention_interval_seconds`. So the most
   surgical adaptation is `monkeypatch.setattr(s,
   "RETENTION_INTERVAL_SECONDS", 0.05)` — one-line change, semantically
   equivalent to the spec's intent (make this iteration's cadence
   small) and operationally equivalent to the original
   class-level monkeypatch's effect on the test instance. Called out
   explicitly here because it deviates one word from the spec's
   prescribed "use `store._config.X`" pattern.

4. **Phase A diagnostic script deletion is permanent.** Per spec A4,
   `scripts/diag_retention_logging.py` was deleted at the end of Phase
   A. The Phase C regression test
   `test_retention_logs_success_even_when_vacuum_fails` captures the H3
   mechanism for future sessions; the diagnostic findings file at
   `dev-logs/2026-04-28_retention-mechanism-diagnostic.md` is the
   authoritative-record artifact.

---

## Test Results

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q
5279 passed, 36 warnings in 64.85s (0:01:04)
```

**Net delta:** 5,269 → 5,279 (+10 tests). Distribution:
- `tests/test_telemetry_store.py`: +8 (test_retention_days_is_config_driven, test_retention_logs_zero_deletion_path, test_retention_logs_success_path, test_retention_logs_success_even_when_vacuum_fails, test_pre_vacuum_disk_headroom_check_aborts_when_insufficient, test_pre_vacuum_disk_headroom_check_proceeds_when_sufficient, test_get_health_snapshot_exposes_required_fields, test_health_snapshot_updates_after_retention).
- `tests/api/test_health.py`: +2 (test_health_endpoint_exposes_evaluation_db_subfields, test_health_endpoint_evaluation_db_populated_after_register).

Vitest unchanged (913). Frontend not modified.

**Mid-session regression caught + fixed:** the initial placement of
`EvaluationStoreConfig` in `argus/core/config.py` (immediately after
`HealthConfig`'s `heartbeat_url` `@property`) accidentally orphaned the
`alert_webhook_url` `@property` from `HealthConfig`. Caught by the full
suite (11 tests in `tests/core/test_health.py`,
`tests/core/test_session2b2_pattern_a.py`, and one integration test);
fix relocated `EvaluationStoreConfig` to AFTER the entire `HealthConfig`
class; all 11 tests recovered.

---

## Self-Assessment

**MINOR_DEVIATIONS** — Phase A's findings shifted the fix shape from the
spec's H1-prescribed 2-line change to the H3-correct deletion-INFO-
before-VACUUM layout. The spec explicitly authorized this contingency
("If Phase A finds a different root cause, adapt the fix shape to
match"). The observability behavior is strictly stronger than the spec's
prescription. Class constants retained as deprecated aliases per the
spec's "Keep the class constants as DEPRECATED aliases" pattern, with
the Judgment Call called out above. Surgical IMPROMPTU-10 test
adaptation targets the instance attribute (one word divergence from
spec's `_config.X` instruction; semantically equivalent).

The migration call site at
`argus/strategies/telemetry_store.py::apply_migrations` is byte-for-byte
unchanged. The Sprint 31.8 VACUUM regression tests at
`tests/strategies/test_telemetry_store_vacuum.py` are byte-for-byte
unchanged. The workflow submodule is unchanged. No bypass flag exists
for the pre-VACUUM headroom check (RULE-039 verified via
`grep -nE "skip.headroom|bypass.headroom|--skip-headroom"
argus/strategies/telemetry_store.py` → empty).

---

## Definition of Done — Verification

- [x] Phase A diagnostic complete; findings written to `dev-logs/2026-04-28_retention-mechanism-diagnostic.md`.
- [x] `scripts/diag_retention_logging.py` deleted post-Phase-A (single-use).
- [x] G2 — `EvaluationStoreConfig` Pydantic model created and registered in standalone-overlay registry.
- [x] `config/evaluation_store.yaml` created with documented defaults.
- [x] G3 — both retention branches log INFO; existing IMPROMPTU-10 success-path log line text adapted with size-MB context.
- [x] G1 — fix applied per Phase A H3 finding (deletion-INFO before VACUUM, not rowcount-before-commit per the spec's H1 hypothesis that Phase A ruled out).
- [x] G4 — pre-VACUUM disk-headroom check active; both branches tested.
- [x] G5 — `/health` endpoint exposes `evaluation_db` subfields; backend tests pass.
- [x] G6 — `docs/operations/evaluation-db-runbook.md` written (~3 pages).
- [x] G7 — 10 new pytest, all passing (≥6 minimum met with margin).
- [x] CLAUDE.md DEF table: DEF-231/232/233/234 strikethrough RESOLVED-IN-SPRINT; DEF-235 OPEN-DEFERRED.
- [x] `docs/decision-log.md`: DEC-389 entry appended.
- [x] `docs/dec-index.md`: DEC-389 line appended; header count updated 387 → 388.
- [x] `docs/sprint-history.md`: Sprint 31.915 row appended.
- [x] Mid-sprint doc-sync manifest written.
- [x] Close-out written to file.
- [ ] Tier 2 review CLEAR or CONCERNS_RESOLVED.
- [ ] Green CI URL cited in close-out.

---

## ---BEGIN-CLOSE-OUT---

```
sprint: 31.915
session: 1
session_title: evaluation.db Retention Mechanism + Observability
self_assessment: MINOR_DEVIATIONS
context_state: GREEN
pre_session_sha: 84d072b
post_session_sha: e58edec
files_modified: 12
files_new: 5
tests_baseline: 5269
tests_total: 5279
tests_new: 10
vitest_baseline: 913
vitest_total: 913
def_resolved_in_sprint: [DEF-231, DEF-232, DEF-233, DEF-234]
def_new_open_deferred: [DEF-235]
dec_added: [DEC-389]
constraint_violations: 0
ci_run_url: TBD
```

## ---END-CLOSE-OUT---

```json:structured-closeout
{
  "sprint": "31.915",
  "session": 1,
  "session_title": "evaluation.db Retention Mechanism + Observability",
  "self_assessment": "MINOR_DEVIATIONS",
  "context_state": "GREEN",
  "pre_session_sha": "84d072b",
  "post_session_sha": "e58edec",
  "files_modified": [
    "CLAUDE.md",
    "argus/api/routes/health.py",
    "argus/api/server.py",
    "argus/core/config.py",
    "argus/core/health.py",
    "argus/main.py",
    "argus/strategies/telemetry_store.py",
    "docs/dec-index.md",
    "docs/decision-log.md",
    "docs/sprint-history.md",
    "tests/api/test_health.py",
    "tests/test_telemetry_store.py"
  ],
  "files_new": [
    "config/evaluation_store.yaml",
    "dev-logs/2026-04-28_retention-mechanism-diagnostic.md",
    "docs/operations/evaluation-db-runbook.md",
    "docs/sprints/sprint-31.915-evaluation-db-retention/doc-sync-manifest.md",
    "docs/sprints/sprint-31.915-evaluation-db-retention/session-1-closeout.md"
  ],
  "tests": {
    "pytest_baseline": 5269,
    "pytest_total": 5279,
    "new": 10,
    "vitest_baseline": 913,
    "vitest_total": 913
  },
  "def_resolved_in_sprint": [
    "DEF-231",
    "DEF-232",
    "DEF-233",
    "DEF-234"
  ],
  "def_new_open_deferred": [
    "DEF-235"
  ],
  "dec_added": [
    "DEC-389"
  ],
  "phase_a_findings": {
    "h1_ruled_out": true,
    "h3_confirmed": true,
    "diagnostic_artifact": "dev-logs/2026-04-28_retention-mechanism-diagnostic.md"
  },
  "judgment_calls": [
    "Phase A confirmed H3 not H1; fix shape adapted to deletion-INFO-before-VACUUM rather than the spec's H1-prescribed rowcount-before-commit",
    "Class constants retained as DEPRECATED aliases synced from _config in __init__ for Sprint 31.8 VACUUM regression-test compat (per the spec's 'Keep the class constants as DEPRECATED aliases' pattern)",
    "IMPROMPTU-10 test surgical adaptation targets instance attribute self.RETENTION_INTERVAL_SECONDS rather than self._config.retention_interval_seconds because production reads the instance attribute"
  ],
  "constraint_violations": 0,
  "ci_run_url": "TBD"
}
```
