# Sprint 31.91 — Impromptu C Tier 2 Review (inline)

> **Sprint / Session:** 31.91 / Impromptu-C.
> **Reviewer:** inline subagent within the implementing Claude Code session per impl prompt §"Tier 2 Review (inline)".
> **Inputs read:** the impl prompt; the `git diff` produced this session; all 7 new migration modules; all 7 new test files; all 7 modified owning services; `argus/data/migrations/__init__.py` + `framework.py` + `operations.py` (template reference); a sample of pre-existing service tests (not modified by Impromptu C).
> **Verdict:** **CLEAR_WITH_NOTES** (3 LOW concerns; all pre-existing tech debt or deferred-fix candidates; none block closeout).

---

## Scope verification

- 7 new migration modules created at `argus/data/migrations/{catalyst,evaluation,regime_history,learning,vix_landscape,counterfactual,experiments}.py` — one per target DB.
- 7 owning services modified to call `apply_migrations(...)` in their `initialize()` method.
- 7 new test files at `tests/data/migrations/test_*.py` + `__init__.py` package marker. 4 tests per file; 28 tests total.
- **Do-not-modify list verified zero diff via `git diff --stat`:** `argus/data/migrations/__init__.py`, `argus/data/migrations/framework.py`, `argus/data/migrations/operations.py`, `argus/main.py`, `argus/api/server.py`.
- No incidental refactoring outside the seven owning-service files.

---

## Review focus areas (per impl prompt §"Tier 2 Review")

### 1. Per-DB migration modules follow the operations.py template exactly

**Status: PASS.** All 7 modules follow the template structurally:

- `from __future__ import annotations`
- `import aiosqlite`
- `from argus.data.migrations.framework import Migration`
- Module-level `SCHEMA_NAME = "..."` constant
- Underscore-prefixed `_xxx_DDL` constants for tables/indexes
- `_migration_001_up(db: aiosqlite.Connection) -> None` async function
- `_migration_001_down(db: aiosqlite.Connection) -> None` advisory inverse
- Module-level `MIGRATIONS: list[Migration]` registry
- Description string starts with "Sprint 31.91 Impromptu C:"

No novel patterns. Schema-name uniqueness verified: `{operations, catalyst, evaluation, regime_history, learning, vix_landscape, counterfactual, experiments}` are all distinct.

### 2. Owning-service call-sites correct

**Status: PASS.** Every service places `apply_migrations` BEFORE any service-specific DDL or data work:

- `CatalystStorage.initialize()`: PRAGMA → `apply_migrations` → legacy `fetched_at` ALTER fallback (covers pre-Sprint-23.6 DBs).
- `EvaluationEventStore.initialize()`: PRAGMA → `apply_migrations` → DB-size observability + startup VACUUM.
- `RegimeHistoryStore.initialize()`: connect → `apply_migrations` → legacy `_migrate_add_vix_close()` → retention cleanup. Ordering matters: framework runs first (creates `regime_snapshots` with `vix_close`), then legacy helper runs to handle pre-Sprint-27.9 DBs whose existing table lacks the column.
- `LearningStore.initialize()`: PRAGMA → `apply_migrations`. No legacy ALTER needed.
- `VIXDataService.initialize()`: opens own aiosqlite connection → `apply_migrations` → existing trust-cache + fetch logic. Sync `_init_db()` retained for sync test API.
- `CounterfactualStore.initialize()`: PRAGMA → `apply_migrations` → legacy `variant_id` + `scoring_fingerprint` ALTER fallbacks (covers pre-Sprint-32.5-S5 / pre-FIX-01 DBs).
- `ExperimentStore.initialize()`: PRAGMA → `apply_migrations` → legacy `exit_overrides` ALTER fallback (covers pre-Sprint-32.5-S1 DBs).

Idempotency: framework itself is idempotent (verified via test 2 per DB); legacy ALTER blocks are guarded with `contextlib.suppress(Exception)`, narrow `OperationalError + msg` check (FIX-08 pattern, ExperimentStore), `try/except Exception: pass` (CounterfactualStore variant_id), or PRAGMA pre-check (CounterfactualStore scoring_fingerprint, RegimeHistoryStore vix_close).

### 3. Existing service tests still pass

**Status: PASS.** Zero modifications to existing service tests. `git diff` of all 9 service-test files returns 0 lines. Sample run of 112 scoped service tests passes in 1.46s. Strongest possible signal of behavioural neutrality.

### 4. The 7 new test files cover the 4 invariants per DB

**Status: PASS.** Every test file uniformly covers all 4 invariants:

- `*_v1_creates_expected_tables` — uses `EXPECTED_TABLES` set; asserts each is in `sqlite_master`.
- `*_v1_is_idempotent` — applies twice; asserts `current_version == 1`, `schema_version` row count == 1.
- `*_v1_preserves_existing_data` — pre-creates table with the FULL v1 schema, inserts a row, applies framework, asserts row survives.
- `*_schema_version_recorded` — asserts `version=1` and description contains "Sprint 31.91".

Naming and structure are uniform across all 7 files; no copy-paste drift in the assertion bodies.

### 5. Pre-existing data preservation

**Status: PASS.** Test 3 per DB exercises this. Each test pre-populates the table with a representative row using the full v1 schema (including columns added by historical in-place ALTERs like `fetched_at`, `vix_close`, `variant_id`, `scoring_fingerprint`, `exit_overrides`); after applying v1, the row is asserted to survive intact.

---

## Architectural concerns (per impl prompt)

### Concern A — Are the legacy ALTER TABLE fallbacks sound?

**Defensible pro-side:** The legacy fallbacks handle a real backward-compat case. Empirically verified: applying v1 to a pre-existing legacy table that lacks `variant_id` / `scoring_fingerprint` / `exit_overrides` / `vix_close` / `fetched_at` does NOT add the columns (because `CREATE TABLE IF NOT EXISTS` is a no-op when the table exists). Without the legacy ALTERs, production DBs would hit `OperationalError: no such column` on first INSERT after Impromptu C. The fallbacks are correctness-critical for upgrade-in-place against existing operator DBs.

**Defensible con-side:** A future engineer reading the code might wonder "why is the ALTER still here if the framework owns the schema?" The in-line comments do call this out (`"Legacy compat: pre-Impromptu-C DBs whose ... pre-dates ..."`), but a future cleanup could introduce a migration v2 in each affected schema that explicitly does `ALTER TABLE ADD COLUMN IF NOT EXISTS` (via PRAGMA table_info pre-check) and retires the post-`apply_migrations` legacy block. That's a follow-up sprint, not a blocker.

**Verdict:** Sound. Comments are adequate.

### Concern B — VIXDataService sync `_init_db()` + async `apply_migrations`: defensible compromise or smell?

**Sync path rationale (verified):** Tests at `tests/data/test_vix_data_service.py` (lines 134, 155, 172, 188, etc.) construct `VIXDataService(...)` and call `service.persist_daily([...])` synchronously WITHOUT awaiting `initialize()`. `_init_db()` runs in `__init__` and creates the table via `CREATE TABLE IF NOT EXISTS`, so `persist_daily()` works without async setup. Removing `_init_db()` would break ~16 tests.

**Defensible compromise:** The async `initialize()` opens a separate aiosqlite connection just to run `apply_migrations`. The sync path's `CREATE TABLE IF NOT EXISTS` and the async path's framework-managed `CREATE TABLE IF NOT EXISTS` produce identical schemas. The sync path doesn't bypass the framework — the framework still runs whenever `initialize()` is called. Production code path always calls `await initialize()` so `schema_version` is always written.

**Subtle smell:** A process that uses ONLY the sync API (constructor + `persist_daily`) never gets `schema_version` written. Artificial test-only scenario today; could be cleaned up in a follow-up. Recorded as LOW concern #3.

**Verdict:** Defensible.

### Concern C — Are the "v1 doesn't add new columns to pre-existing legacy table" comments clear enough?

The CounterfactualStore comment is the densest/most-explicit:

```
# Sprint 31.91 Impromptu C: schema managed by the migration framework.
# Migration v1 includes both the variant_id column (Sprint 32.5 S5)
# and the scoring_fingerprint column (FIX-01) previously added via
# in-place ALTER TABLE; the legacy ALTER fallbacks below cover DBs
# that pre-date the framework adoption AND already have the v1 table
# rows in place — for those, the v1 migration's CREATE TABLE IF NOT
# EXISTS is a no-op and the columns must be added manually.
```

Catalyst, RegimeHistory, and Experiments comments are slightly terser but convey the same point. **Verdict:** Clear enough.

---

## Strengths

- Mechanical scope discipline: 7 modules built to a single template, no creativity.
- Zero diff on the do-not-modify list (5 files, verified via `git diff --stat`).
- Zero edits to existing service tests (9 files, verified via `git diff`) — strongest evidence of behavioural neutrality.
- 28 new tests cover the same 4 invariants per DB; consistent shape across all 7.
- Inline comments at each owning service explain the legacy ALTER fallback rationale.
- Schema names unique across all 8 schemas (verified by import-and-print).
- RegimeHistoryStore ordering correct: framework runs first, legacy `_migrate_add_vix_close()` second.
- Empirical verification: legacy ALTER fallback in CatalystStorage still exercised by pre-existing `test_schema_migration_alter_table` test (PASS confirmed).
- Full suite green: 5266 passed, 0 failed.

---

## Concerns

**LOW (1):** CounterfactualStore `variant_id` ALTER block uses bare `try/except Exception: pass`, inconsistent with FIX-08's narrowed catch pattern used by ExperimentStore. **Pre-existing code carried forward unchanged** — Impromptu C didn't introduce or worsen the inconsistency. Future hygiene pass should align both to the FIX-08 pattern.

**LOW (2):** Legacy ALTER backward-compat paths for `counterfactual_positions.variant_id`, `counterfactual_positions.scoring_fingerprint`, `variants.exit_overrides`, and `regime_snapshots.vix_close` are not directly unit-tested (pre-existing gap, unchanged by Impromptu C). Only `catalyst_events.fetched_at` has dedicated regression coverage. Functionally covered by production usage and end-to-end `initialize()` tests.

**LOW (3):** VIXDataService keeps a sync `_init_db()` for sync-API test compatibility, alongside async `apply_migrations` in `initialize()`. A test process using only the sync API would never get `schema_version` written. Defensible compromise; pure test-only scenario today.

---

## Recommendation

**CLEAR_WITH_NOTES — proceed to closeout.** DEF-223 appropriately RESOLVED-IN-SPRINT by this work; migration framework now spans all 8 ARGUS SQLite DBs (sprint-spec D16 fulfilled). The three LOW concerns are pre-existing tech debt or deferred-fix candidates; none warrant blocking. Closeout explicitly acknowledges all three for future-sprint visibility.

```json
{
  "verdict": "CLEAR_WITH_NOTES",
  "scope_compliance": "CLEAN. All 7 owning-service modifications are in scope; 7 new migration modules + 7 new test files added per spec. Zero diff on the do-not-modify list. Schema names unique across all 8 schemas. No incidental refactoring.",
  "test_coverage": "Strong. 28 new tests (4 invariants × 7 DBs) all pass. Existing service tests (112) all pass with zero modifications. Pre-existing test_schema_migration_alter_table for CatalystStorage's legacy fetched_at ALTER fallback also passes, confirming backward-compat path is alive.",
  "regression_risk": "LOW. Full suite 5266 passed, 0 failed. Empirically verified that v1 framework alone does NOT add columns like variant_id/scoring_fingerprint to a pre-existing legacy table, confirming that the retained legacy ALTER fallbacks are doing real, necessary work for in-place upgrade.",
  "concerns": [
    {
      "severity": "LOW",
      "summary": "CounterfactualStore variant_id ALTER fallback uses bare try/except Exception (pre-existing, unchanged)",
      "detail": "Pre-existing code carried forward unchanged from before Impromptu C. Future hygiene pass should align both to FIX-08 pattern."
    },
    {
      "severity": "LOW",
      "summary": "Legacy ALTER fallbacks for 4 columns lack dedicated unit tests (pre-existing gap)",
      "detail": "counterfactual_positions.variant_id, counterfactual_positions.scoring_fingerprint, variants.exit_overrides, regime_snapshots.vix_close. Functionally covered by production usage and end-to-end initialize() tests."
    },
    {
      "severity": "LOW",
      "summary": "VIXDataService sync _init_db() + async apply_migrations is a defensible test-API compromise",
      "detail": "Sync test API works without async initialize(). Production always calls await initialize(); pure test-only scenario for the never-write-schema_version path."
    }
  ],
  "strengths": [
    "Mechanical template fidelity: 7 modules built to operations.py shape",
    "Zero diff on the do-not-modify list",
    "Zero edits to existing service tests",
    "28 new tests with uniform 4-invariant coverage per DB",
    "Inline comments explain legacy ALTER fallback rationale",
    "Schema-name uniqueness verified across all 8 ARGUS SQLite DBs",
    "Full suite green: 5266 passed, 0 failed"
  ],
  "recommendation": "CLEAR_WITH_NOTES — proceed to closeout. DEF-223 RESOLVED-IN-SPRINT; sprint-spec D16 fulfilled; three LOW concerns deferred."
}
```
