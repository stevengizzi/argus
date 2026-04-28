# Sprint 31.91 — Impromptu C Implementation Prompt: Migration Framework Adoption Sweep

> **Workflow contract:** authored under `templates/implementation-prompt.md` v1.5.0 (structural anchors); references `protocols/mid-sprint-doc-sync.md` v1.0.0 for closeout discipline.
> **Sprint:** 31.91 reconciliation-drift.
> **Position in track:** between Session 5c and Session 5d.
> **Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition.
> **Resolves:** DEF-223 (LOW).
> **Sprint-spec deliverable:** D16.
> **Tier 2 review:** inline within this implementing session.

## CONDITION FOR ENTRY

Sessions through Session 5c must have landed CLEAR. (No specific dependency on Session 5c's content; the dependency is sequential — Impromptu C runs after S5c per the new session order.)

## Pre-Flight

Read the following inputs in full:
- This impl prompt.
- `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended; Item 8 + Concern not separately filed but sprint-spec D16).
- `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` (D16 deliverable + AC).
- `argus/data/migrations/__init__.py`, `framework.py`, `operations.py` — the existing reference pattern.
- For each of the 7 target DBs, the owning service file's existing DDL (find by grep, see Requirement details).

## Scope

Wrap each of the 7 ARGUS SQLite DBs (other than `operations.db`) in a v1 Migration object under the migration framework. Mechanical, low-risk; the architectural value is consistency.

The 7 target DBs:
1. `data/catalyst.db` — owned by `argus/intelligence/catalyst_storage.py`
2. `data/evaluation.db` — owned by `argus/evaluation/evaluation_event_store.py` (or similar; verify by grep)
3. `data/regime_history.db` — owned by `argus/regime/regime_history_store.py` (or similar; verify by grep)
4. `data/learning.db` — owned by `argus/learning/learning_service.py` (or similar; verify by grep)
5. `data/vix_landscape.db` — owned by `argus/regime/vix_data_service.py` (or similar; verify by grep)
6. `data/counterfactual.db` — owned by `argus/counterfactual/counterfactual_store.py` (or similar; verify by grep)
7. `data/experiments.db` — owned by `argus/experiments/experiment_store.py` (or similar; verify by grep)

**Pre-flight grep-verify (for each DB, identify owning service):**
```bash
for db in catalyst evaluation regime_history learning vix_landscape counterfactual experiments; do
    echo "=== $db.db ==="
    grep -rln "data/${db}\.db\|${db}\.db" argus/ --include="*.py" | head -3
done
```

If any DB cannot be associated with a clear owning service, HALT and request operator disposition.

### Requirement 1 — Per-DB migration modules

For each of the 7 DBs, create a new module at `argus/data/migrations/<schema_name>.py` following the `operations.py` template:

```python
"""Migration registry for ``data/<schema_name>.db`` (Sprint 31.91 Impromptu C).

The ``<schema_name>`` schema collects ARGUS's <description> tables.

Version 1 codifies the existing schema as it stood at the start of
Sprint 31.91 Impromptu C. Pre-existing tables created via
``CREATE TABLE IF NOT EXISTS`` are no-ops on re-run.
"""

from __future__ import annotations

import aiosqlite

from argus.data.migrations.framework import Migration

SCHEMA_NAME = "<schema_name>"

# Wrap the existing service module's DDL constants here.
# (Copy verbatim from the owning service's DDL.)

_<SCHEMA>_TABLE_DDL = """..."""


async def _migration_001_up(db: aiosqlite.Connection) -> None:
    """Create all tables required by the existing <schema_name> schema."""
    await db.execute(_<SCHEMA>_TABLE_DDL)
    # ... additional tables ...


async def _migration_001_down(db: aiosqlite.Connection) -> None:
    """Advisory inverse for migration 001 (manual rollback only)."""
    await db.execute("DROP TABLE IF EXISTS <table_1>")
    # ... additional drops in reverse order ...


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description=(
            "Sprint 31.91 Impromptu C: <schema_name> schema (existing "
            "tables wrapped into migration framework)"
        ),
        up=_migration_001_up,
        down=_migration_001_down,
    ),
]
```

### Requirement 2 — Wire each owning service to call apply_migrations

For each owning service, find the existing initialization code that creates tables (typically in an `_initialize_schema` or `_ensure_schema` method, or inline in `__init__` / `start`). The structural anchor is the first DDL execution in the owning service.

**Replace** the existing DDL execution with a call to `apply_migrations`:

```python
from argus.data.migrations import apply_migrations
from argus.data.migrations.<schema_name> import SCHEMA_NAME, MIGRATIONS

# ... in __init__ or start ...
async with aiosqlite.connect(self._db_path) as db:
    await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
```

The existing `CREATE TABLE IF NOT EXISTS` pattern preserves existing data, so applying v1 to a DB that pre-dates the framework is safe.

### Requirement 3 — Per-DB tests

For each of the 7 DBs, create a corresponding test at `tests/data/migrations/test_<schema_name>.py` following the existing test pattern in `tests/api/test_alerts_5a2.py` (the `test_apply_migrations_is_idempotent`, `test_schema_version_records_v1` shape).

Test cases per DB:
1. `test_<schema_name>_v1_creates_expected_tables` — apply v1; verify each table exists via `sqlite_master` query.
2. `test_<schema_name>_v1_is_idempotent` — apply v1 twice; verify no errors and `schema_version` row exists once.
3. `test_<schema_name>_v1_preserves_existing_data` — pre-create a row in the schema's main table; apply v1; verify the row still exists.
4. `test_<schema_name>_schema_version_recorded` — apply v1; verify `schema_version` table contains a row with `schema_name=<schema_name>` and `version=1`.

## Scope Boundaries (do-not-modify)

- `argus/data/migrations/__init__.py`, `framework.py`, `operations.py` — zero edits (the framework is now stable).
- `argus/main.py`, `argus/api/server.py` — zero edits this impromptu (services own their own migration calls).
- All non-data-storage code paths — zero edits.

## Behavioral invariants

After Impromptu C:
- All 8 ARGUS SQLite DBs are managed by the migration framework.
- Each owning service's `start()` or `__init__` calls `apply_migrations` before any other DDL.
- `schema_version` table exists in each DB with one row per DB.
- All existing service-level tests pass without modification (no behavior change).

## Tier 2 Review (inline)

After implementation, spawn a Tier 2 review subagent within this same Claude Code session.

Review focus areas:
1. Each per-DB migration module follows the operations.py template exactly (no novel patterns).
2. Each owning service's call site is in the right place (before any other DDL; idempotent on multi-start).
3. All existing service tests still pass (no regression).
4. The 7 new test files correctly cover the 4 invariants per DB.
5. Pre-existing data is preserved on framework adoption (test 3 per DB).

Verdict format: structured JSON.

## Definition of Done

- [ ] 7 new migration modules created under `argus/data/migrations/`.
- [ ] 7 owning services modified to call `apply_migrations` at startup.
- [ ] 7 new test files; all tests green.
- [ ] All existing service tests pass (no regression).
- [ ] Full test suite passes: `python -m pytest --ignore=tests/test_main.py -n auto -q`.
- [ ] Test count increases by approximately 28 (4 tests × 7 DBs).
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-c-closeout.md`.
- [ ] Tier 2 review at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-c-review.md`.

## Closeout requirements

Per `protocols/mid-sprint-doc-sync.md` v1.0.0 + the manifest pattern:
- `mid_sprint_doc_sync_ref: "docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md"`.
- DEF transitions claimed: DEF-223 → "RESOLVED-IN-SPRINT, Impromptu C".
- Architecture catalog note: migration framework now spans all 8 ARGUS SQLite DBs (architecture.md update at sprint-close).
- Anchor commit SHA.
- Tier 3 track marker: `migration-framework-adoption` (new track marker for sprint-close attribution).
