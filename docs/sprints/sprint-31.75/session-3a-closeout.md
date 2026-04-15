---BEGIN-CLOSE-OUT---

**Session:** Sprint 31.75, Session 3a — DuckDB Persistence
**Date:** 2026-04-14
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/data/historical_query_config.py` | modified | Added `persist_path: str | None` field |
| `argus/data/historical_query_service.py` | modified | Persistent DB mode in `__init__()`, added `rebuild()` method |
| `config/historical_query.yaml` | modified | Added `persist_path: null` with comment |
| `scripts/run_experiment.py` | modified | Added `--persist-db`, `--rebuild` flags; `persist_path` param on `_apply_universe_filter` + `_validate_coverage`; `persist_db` determination + `--rebuild` early-exit + pre-filtering in `run()` |
| `.gitignore` | modified | Added `*.duckdb` and `*.duckdb.wal` |
| `tests/data/test_historical_query_service.py` | modified | Added 6 new persistent mode tests in `TestPersistentMode` class |

### Judgment Calls
Decisions made during implementation that were NOT specified in the prompt:

- **Pre-filtering in `run()` clears `filter_config`**: When `--universe-filter` is used for a real run (non-dry-run), `run()` now calls `_apply_universe_filter()` + `_validate_coverage()` with the persistent DB, sets `symbols` to the resolved list, and passes `universe_filter=None` to the runner. This replaces the runner's internal cold-init filtering. Rationale: the spec says to "thread `args.persist_db` through to `_apply_universe_filter()` and `_validate_coverage()` calls" — since these functions were not previously called in `run()`, calls had to be added. This is the only interpretation that makes the persistent DB actually speed up the universe-filter workflow (the runner's internal service creation cannot be modified per constraints).
- **Dry-run skips pre-filtering**: Pre-filtering with the persistent DB only happens for real (non-dry-run) runs. Dry-run retains the existing "resolved at sweep time" message. Rationale: dry runs should be fast and should not hit the cache.
- **`effective_db` fallback in `--rebuild`**: If `--rebuild` is used without `--universe-filter` and without `--persist-db`, the effective path defaults to `"data/historical_query.duckdb"`. This mirrors the auto-default behavior and ensures `--rebuild` always has a target path.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Add `persist_path` to `HistoricalQueryConfig` | DONE | `historical_query_config.py:29-37` |
| Persistent DB uses `duckdb.connect(database=path)` | DONE | `historical_query_service.py:__init__` |
| VIEW existence check via `duckdb_views()` | DONE | `historical_query_service.py:__init__` |
| Skip `_initialize_view()` when VIEW exists | DONE | `historical_query_service.py:__init__` |
| Log persistent mode usage | DONE | `historical_query_service.py:__init__` |
| `:memory:` mode unchanged when `persist_path=None` | DONE | No code change to that path |
| `rebuild()` method implemented | DONE | `historical_query_service.py:rebuild()` |
| `config/historical_query.yaml` updated | DONE | `persist_path: null` with comment |
| `--persist-db` CLI flag | DONE | `scripts/run_experiment.py:parse_args()` |
| `--rebuild` CLI flag | DONE | `scripts/run_experiment.py:parse_args()` |
| `persist_path` param on `_apply_universe_filter` | DONE | `scripts/run_experiment.py:_apply_universe_filter()` |
| `persist_path` param on `_validate_coverage` | DONE | `scripts/run_experiment.py:_validate_coverage()` |
| Thread `persist_db` through to their calls | DONE | `run()` calls both functions with `persist_path=persist_db` |
| Auto-default `"data/historical_query.duckdb"` when `--universe-filter` used | DONE | `run()` sets `persist_db` from auto-default |
| `--rebuild` exits after rebuilding, no sweeps | DONE | Early return at top of `run()` |
| `.duckdb` and `.duckdb.wal` in `.gitignore` | DONE | `.gitignore` |
| 5+ new tests | DONE | 6 tests in `TestPersistentMode` |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| `:memory:` mode still works | PASS | All 436 pre-existing tests pass unchanged |
| `run_experiment.py --dry-run` exits 0 | PASS | `python scripts/run_experiment.py --pattern bull_flag --dry-run` exits 0 |
| No schema changes to `store.py` | PASS | `git diff argus/intelligence/experiments/store.py` is empty |
| Config backward compatible (no errors loading existing YAML) | PASS | `test_yaml_loads_into_config` still passes; `persist_path: null` accepted |

### Test Results
- Tests run: 442
- Tests passed: 442
- Tests failed: 0
- New tests added: 6
- Command used: `python -m pytest tests/data/ -x -q`

### Unfinished Work
None.

### Notes for Reviewer
- The `duckdb_views()` system function is the correct approach (not try/except on a SELECT); verify this in the diff at `historical_query_service.py`.
- `:memory:` mode path is completely unchanged: the `config.persist_path is None` branch falls through to the original `self._initialize_view(cache_path)` call without any new code paths.
- `rebuild()` calls `_initialize_view()` which uses `CREATE OR REPLACE VIEW` — this drops+recreates the VIEW on the existing connection (not a reconnect).
- `--rebuild` returns 0 immediately after `service.rebuild()` + `service.close()` + print; no parameter grid generation or sweep execution happens.
- `.duckdb.wal` is present in `.gitignore` (DuckDB WAL files).
- All paths use `str(Path(...))` or forward-slash strings — no Windows-specific path issues introduced.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "31.75",
  "session": "3a",
  "verdict": "COMPLETE",
  "tests": {
    "before": 436,
    "after": 442,
    "new": 6,
    "all_pass": true
  },
  "files_created": [],
  "files_modified": [
    "argus/data/historical_query_config.py",
    "argus/data/historical_query_service.py",
    "config/historical_query.yaml",
    "scripts/run_experiment.py",
    ".gitignore",
    "tests/data/test_historical_query_service.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "run() now calls _apply_universe_filter() + _validate_coverage() for non-dry-run universe-filter sweeps, pre-resolving symbols before the runner",
      "justification": "The spec says to thread persist_db through to calls of these functions. They were not previously called in run(). Adding the calls is the only way to make the persistent DB speed up the universe-filter workflow, since runner.py cannot be modified per constraints."
    }
  ],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Persistent DB mode connects via duckdb.connect(database=path). VIEW existence is checked with duckdb_views() system table. When VIEW exists, _initialize_view is skipped and _available is set True immediately. rebuild() resets _available/_symbols_cache and calls _initialize_view() which uses CREATE OR REPLACE VIEW. The :memory: code path is structurally identical to the original — no new branches when persist_path is None."
}
```
