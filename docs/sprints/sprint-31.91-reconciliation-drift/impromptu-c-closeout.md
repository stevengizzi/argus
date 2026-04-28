# Sprint 31.91 — Impromptu C Close-Out

> **Track:** Migration Framework Adoption Sweep (post-Tier-3-#2).
> **Tier 3 track marker:** `migration-framework-adoption` (new track marker for sprint-close attribution).
> **Position in track:** Between Session 5c (CLEAR, commit `41e49e7`) and Session 5d.
> **Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition (Item 8 / sprint-spec D16).
> **Resolves:** DEF-223 (LOW — migration framework adoption sweep across the 7 ARGUS SQLite DBs other than `operations.db`).
> **Self-assessment:** **PROPOSED_CLEAR_WITH_NOTES.** Three LOW Tier 2 notes recorded; none blocking. All three are pre-existing tech debt or deferred-fix candidates carried forward without being made worse.
> **Mid-sprint doc-sync ref:** `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md`.
> **Anchor commit SHA:** `d4eff4d` on `main` (HITL-on-main; pre-impromptu HEAD).

---

## Pre-Flight Verification (RULE-038)

The impl prompt's CONDITION FOR ENTRY is "Sessions through Session 5c must have landed CLEAR" — verified at session start via:

| Anchor | Verified |
|---|---|
| Session 5c review verdict at `docs/sprints/sprint-31.91-reconciliation-drift/session-5c-review.md` (or successor) is CLEAR. | ✅ Last commit `41e49e7 chore(sprint-31.91): Session 5c Tier 2 review — CLEAR_WITH_NOTES` confirms. |
| `argus/data/migrations/{__init__.py,framework.py,operations.py}` exist and present the framework template. | ✅ All three files present and unchanged. |
| Each of the 7 target DBs has a clearly identifiable owning service file. | ✅ Mapped via grep: catalyst→`argus/intelligence/storage.py`, evaluation→`argus/strategies/telemetry_store.py`, regime_history→`argus/core/regime_history.py`, learning→`argus/intelligence/learning/learning_store.py`, vix_landscape→`argus/data/vix_data_service.py`, counterfactual→`argus/intelligence/counterfactual_store.py`, experiments→`argus/intelligence/experiments/store.py`. |

No drift reported.

---

## Change Manifest

### New code (7 migration modules)

Each follows the `argus/data/migrations/operations.py` template exactly: `SCHEMA_NAME` constant, underscore-prefixed `_xxx_DDL` constants, `_migration_001_up` async function, `_migration_001_down` advisory inverse, module-level `MIGRATIONS: list[Migration]` registry. All schema names unique across the 8 ARGUS SQLite DBs.

| Module | Schema | v1 wraps |
|---|---|---|
| `argus/data/migrations/catalyst.py` | `catalyst` | `catalyst_events` (incl. `fetched_at` from Sprint 23.6 in-place ALTER) + `catalyst_classifications_cache` + `intelligence_briefs`; 7 indexes |
| `argus/data/migrations/evaluation.py` | `evaluation` | `evaluation_events` + 2 indexes |
| `argus/data/migrations/regime_history.py` | `regime_history` | `regime_snapshots` (incl. `vix_close` from Sprint 27.9 in-place ALTER) + 2 indexes |
| `argus/data/migrations/learning.py` | `learning` | `learning_reports` + `config_proposals` + `config_change_history` + 4 indexes |
| `argus/data/migrations/vix_landscape.py` | `vix_landscape` | `vix_daily` |
| `argus/data/migrations/counterfactual.py` | `counterfactual` | `counterfactual_positions` (incl. `variant_id` from Sprint 32.5 S5 + `scoring_fingerprint` from FIX-01) + 4 indexes |
| `argus/data/migrations/experiments.py` | `experiments` | `experiments` + `variants` (incl. `exit_overrides` from Sprint 32.5 S1) + `promotion_events` + 8 indexes |

### Modified code (7 owning services)

For each owning service: removed module-level / class-attr DDL constants, added `apply_migrations(...)` call in `initialize()`, retained legacy in-place ALTER fallbacks where backward compat with pre-Impromptu-C DBs requires it.

| File | Behaviour change |
|---|---|
| `argus/intelligence/storage.py` (CatalystStorage) | DDL class-attrs removed. `apply_migrations` call added. Legacy `ALTER TABLE catalyst_events ADD COLUMN fetched_at` retained inside `contextlib.suppress(Exception)` for pre-Sprint-23.6 DBs. Pre-existing test at `tests/api/test_intelligence_routes.py::TestSprint236Fixes::test_schema_migration_alter_table` continues to PASS. |
| `argus/strategies/telemetry_store.py` (EvaluationEventStore) | Module-level DDL constants removed. `apply_migrations` call added in `initialize()`. No legacy ALTER needed (table has no in-place column additions in its history). |
| `argus/core/regime_history.py` (RegimeHistoryStore) | Module-level DDL constants removed. `apply_migrations` call added in `initialize()` BEFORE the legacy `_migrate_add_vix_close()` helper which is preserved to handle pre-Sprint-27.9 DBs. |
| `argus/intelligence/learning/learning_store.py` (LearningStore) | Module-level DDL constants removed. `apply_migrations` call added in `initialize()`. No legacy ALTER needed. |
| `argus/data/vix_data_service.py` (VIXDataService) | Sync `_init_db()` retained (sync test API still constructs the service and calls sync `persist_daily()` without awaiting `initialize()`). Async `initialize()` now opens an aiosqlite connection and calls `apply_migrations` before existing trust-cache logic. |
| `argus/intelligence/counterfactual_store.py` (CounterfactualStore) | Module-level DDL constants removed. `apply_migrations` call added in `initialize()`. Legacy ALTER fallbacks (`variant_id` + `scoring_fingerprint`) retained for pre-Impromptu-C DBs. |
| `argus/intelligence/experiments/store.py` (ExperimentStore) | Module-level DDL constants removed. `apply_migrations` call added in `initialize()`. Legacy ALTER fallback (`variants.exit_overrides`) retained for pre-Sprint-32.5-S1 DBs. |

### New tests

`tests/data/migrations/__init__.py` + 7 test files (4 tests each = 28 new tests):

| Test file | Schema |
|---|---|
| `tests/data/migrations/test_catalyst.py` | catalyst |
| `tests/data/migrations/test_evaluation.py` | evaluation |
| `tests/data/migrations/test_regime_history.py` | regime_history |
| `tests/data/migrations/test_learning.py` | learning |
| `tests/data/migrations/test_vix_landscape.py` | vix_landscape |
| `tests/data/migrations/test_counterfactual.py` | counterfactual |
| `tests/data/migrations/test_experiments.py` | experiments |

Each file uniformly covers four invariants:
1. `*_v1_creates_expected_tables` — apply v1; assert each expected table appears in `sqlite_master`.
2. `*_v1_is_idempotent` — apply v1 twice; `current_version == 1`; `schema_version` row count == 1.
3. `*_v1_preserves_existing_data` — pre-create the legacy schema with the full v1 column set, insert a row, apply v1, assert row survives.
4. `*_schema_version_recorded` — assert `version=1` and description starts with "Sprint 31.91".

### Files not modified (do-not-modify list — verified zero diff via `git diff --stat`)

- `argus/data/migrations/__init__.py`
- `argus/data/migrations/framework.py`
- `argus/data/migrations/operations.py`
- `argus/main.py`
- `argus/api/server.py`

---

## Test Counts

**Targeted (Impromptu-C scope):**
- New migration tests: 28 PASS (all green in 0.11s).
- Scoped service tests (9 owning-service test files): 112 PASS in 1.46s.
- Pre-existing legacy ALTER fallback test for catalyst `fetched_at` (`tests/api/test_intelligence_routes.py::TestSprint236Fixes::test_schema_migration_alter_table`): PASS.

**Full suite (RULE-019 baseline gate):**
- `python -m pytest --ignore=tests/test_main.py -n auto -q` → **5266 passed, 0 failed in 62.21s.**
- Pre-Impromptu-C baseline (CLAUDE.md as of 2026-04-28): 5080 pytest. Net delta: +186 tests. The 28 explicitly added by Impromptu C account for ~15% of the delta; the rest reflect Sessions 5b/5c + Impromptu A + Impromptu B test additions that landed on `main` between the CLAUDE.md snapshot and this impromptu's start.

---

## Self-Assessment

**PROPOSED_CLEAR_WITH_NOTES.** No spec deviations. Three Tier 2 LOW notes carried as deferred items, none blocking:

1. **CounterfactualStore `variant_id` ALTER catch is `except Exception: pass`** — inconsistent with FIX-08's narrowed catch pattern adopted by `ExperimentStore` (`except aiosqlite.OperationalError as exc: if "duplicate column name" not in str(exc).lower(): raise`). **Pre-existing code carried forward unchanged**; Impromptu C did not introduce or worsen the inconsistency. Future hygiene pass to align both to the FIX-08 pattern.
2. **Legacy ALTER fallback paths for 4 columns lack dedicated unit tests** — `counterfactual_positions.variant_id`, `counterfactual_positions.scoring_fingerprint`, `variants.exit_overrides`, and `regime_snapshots.vix_close`. Only `catalyst_events.fetched_at` has a dedicated regression test (the pre-existing `test_schema_migration_alter_table`). **Pre-existing gap unchanged by Impromptu C.** Functionally covered by production usage and end-to-end `initialize()` tests; worth a follow-up session adding dedicated coverage.
3. **VIXDataService sync `_init_db()` + async `apply_migrations` is a defensible test-API compromise** — sync `_init_db()` in `__init__` keeps the sync test API working (constructor + `persist_daily()` without awaiting `initialize()`). Async `initialize()` opens a separate aiosqlite connection just to run `apply_migrations`. A process that uses ONLY the sync API would never write `schema_version`. Pure test-only scenario today; production always calls `await initialize()`. Cleanup candidate for a future refactor (either making the helper async or providing a sync-mode framework path).

All three are LOW severity, all three are deferred-fix candidates, none warrant blocking the closeout.

---

## DEF Transitions

| DEF | Status before | Status after | Disposition |
|---|---|---|---|
| DEF-223 (LOW — migration framework adoption sweep) | OPEN | RESOLVED-IN-SPRINT, Impromptu C | All 8 ARGUS SQLite DBs are now managed by the migration framework. Each owning service's `initialize()` calls `apply_migrations` before any other DDL. Each DB's `schema_version` row records v1. |

---

## Architecture Catalog Note (queued for sprint-close doc-sync)

Migration framework now spans all 8 ARGUS SQLite DBs. `docs/architecture.md`'s Schema / Storage section should be updated at sprint-close to reflect:
- The 8 schemas managed by `apply_migrations`: `operations` (Sprint 31.91 5a.2) + `catalyst` / `evaluation` / `regime_history` / `learning` / `vix_landscape` / `counterfactual` / `experiments` (all Sprint 31.91 Impromptu C).
- Each schema has a v1 migration that codifies the existing schema as it stood at Sprint 31.91 Impromptu C, including any prior in-place ALTER TABLE additions (`fetched_at`, `vix_close`, `variant_id`, `scoring_fingerprint`, `exit_overrides`).
- Future schema changes register a `Migration` in the appropriate per-DB module rather than executing ad-hoc DDL at random call sites.

---

## Closeout Hand-Off

- Tier 2 review verdict: **CLEAR_WITH_NOTES** (recorded at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-c-review.md`).
- DEF-223 marked RESOLVED-IN-SPRINT, Impromptu C in this closeout (CLAUDE.md DEF-table update queued for sprint-close).
- 3 LOW deferred items recorded in §Self-Assessment for future visibility (architectural hygiene, not blocking).
- Anchor commit: `d4eff4d`.
- Tier 3 track marker: `migration-framework-adoption` (single-session track; sprint-close attribution).
