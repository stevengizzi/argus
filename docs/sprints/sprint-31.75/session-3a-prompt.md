# Sprint 31.75, Session 3a: DuckDB Persistence

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/data/historical_query_service.py`
   - `argus/data/historical_query_config.py`
   - `config/historical_query.yaml`
   - `scripts/run_experiment.py` (lines 230–288: _apply_universe_filter, _validate_coverage)
2. Run the scoped test baseline (DEC-328):
   `python -m pytest tests/data/ -x -q`
   Expected: all passing (full suite confirmed by S2 close-out)
3. Verify you are on the `main` branch
4. Verify S2 close-out was committed

## Objective
Add a persistent DuckDB database mode to HistoricalQueryService so that the
`CREATE VIEW` over 24,321 Parquet files happens once, not on every invocation.
This eliminates the multi-minute initialization that forced overnight sweeps to
use pre-resolved symbol lists instead of `--universe-filter` directly.

## Requirements

### 1. Add `persist_path` to HistoricalQueryConfig

In `argus/data/historical_query_config.py`, add:
```python
persist_path: str | None = Field(
    default=None,
    description=(
        "Path to persistent DuckDB database file. When set, the VIEW is "
        "created once and survives across invocations. When None, uses "
        "in-memory mode (legacy behavior)."
    ),
)
```

### 2. Update HistoricalQueryService initialization

In `argus/data/historical_query_service.py`, modify `__init__()`:

a. When `config.persist_path` is set:
   - Use `duckdb.connect(database=config.persist_path)` instead of `":memory:"`.
   - Check if the `historical` VIEW already exists:
     ```python
     existing = conn.execute(
         "SELECT count(*) FROM duckdb_views() WHERE view_name = 'historical'"
     ).fetchone()[0]
     ```
   - If the VIEW exists, skip `_initialize_view()` and set `self._available = True`.
   - If the VIEW does not exist, call `_initialize_view()` as before.
   - Log the mode: `"HistoricalQueryService: using persistent DB at {path}"` or
     `"HistoricalQueryService: persistent DB opened — VIEW already exists"`.

b. When `config.persist_path` is None:
   - Existing `:memory:` behavior, unchanged.

c. Add a `rebuild()` method for forcing VIEW recreation on a persistent DB:
   ```python
   def rebuild(self) -> None:
       """Force recreation of the historical VIEW.

       Use when the Parquet cache has been updated and the persistent
       DB's VIEW is stale. Only meaningful for persistent mode.

       Raises:
           ServiceUnavailableError: If service is not initialized.
       """
       if not self._conn:
           raise ServiceUnavailableError("Service not initialized")
       cache_path = Path(self._config.cache_dir)
       if not cache_path.exists():
           raise ServiceUnavailableError(f"Cache dir missing: {cache_path}")
       self._available = False
       self._symbols_cache = None
       self._initialize_view(cache_path)
   ```

### 3. Update config YAML

In `config/historical_query.yaml`, add:
```yaml
  persist_path: null  # Set to "data/historical_query.duckdb" for persistent mode
```

### 4. Wire persistent mode in run_experiment.py

In `scripts/run_experiment.py`:

a. Modify `_apply_universe_filter()` and `_validate_coverage()` to accept an
   optional `persist_path` parameter. When provided, pass it through to
   `HistoricalQueryConfig`:
   ```python
   service = HistoricalQueryService(
       HistoricalQueryConfig(
           enabled=True,
           cache_dir=cache_dir,
           persist_path=persist_path,
       )
   )
   ```

b. Add a `--persist-db` CLI flag:
   ```python
   parser.add_argument(
       "--persist-db",
       type=str,
       default=None,
       help="Path to persistent DuckDB file (speeds up repeated runs)",
   )
   ```

c. Thread `args.persist_db` through to `_apply_universe_filter()` and
   `_validate_coverage()` calls. Default to
   `"data/historical_query.duckdb"` when `--universe-filter` is used
   and `--persist-db` is not explicitly set (opt-in automatic persistence
   for universe filter workflows).

### 5. Add `--rebuild` flag to CLI

In `scripts/run_experiment.py`, add:
```python
parser.add_argument(
    "--rebuild",
    action="store_true",
    help="Rebuild the persistent DuckDB VIEW (use after cache updates)",
)
```

When `--rebuild` is set and `--persist-db` is provided (or defaulted):
- Open the persistent DB
- Call `service.rebuild()`
- Close and exit with a success message
- Do NOT run any sweeps

### 6. Add `.duckdb` to .gitignore

Ensure `*.duckdb` and `*.duckdb.wal` are in `.gitignore` (the persistent DB
should never be committed).

## Constraints
- Do NOT modify: `argus/intelligence/experiments/runner.py` (runner doesn't
  create HistoricalQueryService — the CLI script does)
- Do NOT modify: `argus/intelligence/experiments/store.py`
- Do NOT modify: any pattern files
- Do NOT remove or change behavior of `:memory:` mode — it must remain the
  default when `persist_path` is None
- Do NOT modify the `historical` VIEW SQL — same columns, same logic
- Do NOT change the REST endpoints for historical queries

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:

  1. `test_persistent_mode_creates_db_file` — instantiate with persist_path
     pointing to a temp file, verify the file is created.
  2. `test_persistent_mode_reuses_view` — create service with persist_path,
     close it, create a new service with same persist_path, verify VIEW exists
     without re-creation (check log or mock `_initialize_view`).
  3. `test_memory_mode_unchanged` — persist_path=None uses `:memory:` (existing behavior).
  4. `test_rebuild_recreates_view` — call rebuild(), verify VIEW is recreated.
  5. `test_config_persist_path_field` — verify HistoricalQueryConfig accepts
     persist_path as str or None.
  6. `test_gitignore_has_duckdb` — read .gitignore, verify `*.duckdb` pattern present.

- Minimum new test count: 5
- Test command: `python -m pytest tests/data/ -x -q`

## Config Validation
Write a test that loads `config/historical_query.yaml` and verifies all keys
under `historical_query:` are recognized by `HistoricalQueryConfig`:

| YAML Key | Model Field |
|----------|-------------|
| enabled | enabled |
| cache_dir | cache_dir |
| max_memory_mb | max_memory_mb |
| default_threads | default_threads |
| persist_path | persist_path |

## Definition of Done
- [ ] HistoricalQueryConfig has persist_path field
- [ ] HistoricalQueryService uses persistent DB when persist_path is set
- [ ] VIEW check skips re-creation when persistent DB already has VIEW
- [ ] rebuild() method implemented
- [ ] :memory: mode unchanged (backward compatible)
- [ ] run_experiment.py has --persist-db and --rebuild flags
- [ ] --universe-filter defaults to persistent mode
- [ ] .gitignore updated for *.duckdb
- [ ] config/historical_query.yaml updated
- [ ] All existing tests pass
- [ ] 5+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| :memory: mode still works | Existing historical query tests pass unchanged |
| run_experiment.py --dry-run still works | `python scripts/run_experiment.py --pattern bull_flag --dry-run` exits 0 |
| No schema changes | `git diff argus/intelligence/experiments/store.py` shows no changes |
| Config backward compatible | Load existing config/historical_query.yaml — no errors |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-31.75/session-3a-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-31.75/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.75/session-3a-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/data/ -x -q`
5. Files that should NOT have been modified: `argus/intelligence/experiments/runner.py`, `argus/intelligence/experiments/store.py`, any pattern files, any `ui/` files

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-31.75/session-3a-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review report files per the standard
protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify the persistent DB check uses `duckdb_views()` system table, not
   a try/except on `SELECT * FROM historical LIMIT 1` (which would mask
   other errors).
2. Verify `:memory:` mode is truly unchanged — no new code paths when
   persist_path is None.
3. Verify `rebuild()` drops and recreates the VIEW, not just the connection.
4. Verify `--rebuild` exits after rebuilding without running sweeps.
5. Verify `.duckdb.wal` is also in .gitignore (DuckDB WAL files).
6. Verify that the persistent DB file path uses forward slashes or
   Path objects consistently (cross-platform safety).

## Sprint-Level Regression Checklist (for @reviewer)
(See review-context.md)

## Sprint-Level Escalation Criteria (for @reviewer)
(See review-context.md)
