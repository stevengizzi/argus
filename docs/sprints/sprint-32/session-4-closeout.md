# Sprint 32, Session 4 — Close-Out Report

## Self-Assessment: CLEAN

## Change Manifest

### New Files Created
| File | Purpose |
|------|---------|
| `argus/intelligence/experiments/__init__.py` | Package init — exports 5 public symbols |
| `argus/intelligence/experiments/models.py` | `ExperimentStatus`, `VariantDefinition`, `ExperimentRecord`, `PromotionEvent` |
| `argus/intelligence/experiments/store.py` | `ExperimentStore` — 3-table SQLite registry |
| `tests/intelligence/experiments/__init__.py` | Test package init |
| `tests/intelligence/experiments/test_store.py` | 13 tests covering all CRUD paths |

### Modified Files
None — `git diff --name-only` is empty (only new files).

## Scope Verification

| Requirement | Status |
|-------------|--------|
| `ExperimentStatus` StrEnum with 8 values | ✅ |
| `VariantDefinition` frozen dataclass | ✅ |
| `ExperimentRecord` mutable dataclass | ✅ |
| `PromotionEvent` frozen dataclass | ✅ |
| `ExperimentStore.initialize()` — WAL + DDL | ✅ |
| `save_experiment` / `get_experiment` / `list_experiments` | ✅ |
| `get_baseline` / `set_baseline` (atomic unmark/mark) | ✅ |
| `save_variant` / `list_variants` / `get_variant` / `update_variant_mode` | ✅ |
| `save_promotion_event` / `list_promotion_events` | ✅ |
| `enforce_retention` — deletes across all 3 tables, returns count | ✅ |
| `close()` — no-op (per-operation connections) | ✅ |
| No circular imports (`from argus.intelligence.experiments import ExperimentStore` succeeds) | ✅ |
| Separate DB file: `data/experiments.db` | ✅ |
| JSON serialization for `backtest_result` and `comparison_verdict` | ✅ |
| ULID usage via `argus.core.ids.generate_id()` | ✅ (used in tests; store accepts pre-generated IDs per DEC-026 pattern) |
| DEC-345 pattern: WAL mode, fire-and-forget, rate-limited warnings | ✅ |
| No existing files modified | ✅ |

## Judgment Calls

1. **Per-operation connections vs. persistent connection** — Followed `learning_store.py` (per-operation `aiosqlite.connect()`) rather than `counterfactual_store.py` (persistent connection held open), since `learning_store.py` was the primary reference in the spec. This is the simpler pattern and equally correct.

2. **`close()` as no-op** — Since the store uses per-operation connections, there is no persistent connection to close. `close()` is provided as required by the spec but is a documented no-op.

3. **`enforce_retention` counts across all 3 tables** — The spec says "delete old records, return count deleted." Deleting from all 3 tables and returning the total provides the most useful signal to callers.

4. **`set_baseline` fetches `pattern_name` inside the same connection** — Atomicity is maintained within a single `aiosqlite.connect()` context: fetch pattern_name → unmark previous → mark new → commit. No TOCTOU window.

5. **Fire-and-forget write test uses uninitialized store** — `test_fire_and_forget_write_does_not_raise_on_bad_db` skips `initialize()` and writes to `/nonexistent_dir/`. aiosqlite raises `OperationalError` which is caught and rate-limited, never propagated. Verified passing.

## Regression Checks

| Check | Result |
|-------|--------|
| `git diff --name-only` — only new files | ✅ Empty (no modifications) |
| `python -c "from argus.intelligence.experiments import ExperimentStore"` | ✅ "Import OK" |
| `python -m pytest tests/test_runtime_wiring.py tests/strategies/patterns/test_factory.py -q` | ✅ 61/61 |
| `python -m pytest tests/intelligence/experiments/ -v` | ✅ 13/13 |

## Test Count Delta

- Before: baseline 61 scoped tests
- After: +13 new tests in `tests/intelligence/experiments/test_store.py`
- Minimum required by spec: 10 ✅ (delivered 13)

## Context State: GREEN
Session completed well within context limits. Single-objective session.
