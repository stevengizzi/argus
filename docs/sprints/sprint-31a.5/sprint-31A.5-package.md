# Sprint 31A.5 — Historical Query Layer (DuckDB Phase 1)

**Sprint type:** Impromptu (additive infrastructure, no regression risk to existing components)
**Urgency:** DISCOVERED (identified during strategic research, unlocks Sprint 31.5+ acceleration)
**Parent sprint:** 31A (Pattern Expansion III — in progress, final session running)
**Sprint sub-number:** 31A.5

---

## Impact Assessment

### 1. Files Touched

**New files (no overlap with any existing code):**
- `argus/data/historical_query_service.py` — core DuckDB service
- `argus/data/historical_query_config.py` — Pydantic config model
- `config/historical_query.yaml` — default config
- `scripts/query_cache.py` — interactive CLI tool
- `tests/data/test_historical_query_service.py` — service tests
- `tests/data/test_historical_query_config.py` — config tests
- `tests/api/test_historical_routes.py` — API endpoint tests
- `argus/api/routes/historical.py` — REST endpoints
- `docs/sprints/sprint-31A.5/` — close-out and review reports

**Modified files (minimal, additive-only changes):**
- `argus/core/config.py` — add `HistoricalQueryConfig` to `SystemConfig` (new optional field)
- `config/system.yaml` — add `historical_query:` section
- `config/system_live.yaml` — add `historical_query:` section
- `argus/api/server.py` — register `HistoricalQueryService` in lifespan (lazy init pattern)
- `argus/api/server.py` — include historical router

### 2. What Could This Break?

**Regression risk: VERY LOW.** All new files. The only modifications to existing files are:
- Adding a new optional field to SystemConfig (backward-compatible, defaults to disabled)
- Adding a new router include in server.py (isolated, no interaction with existing routes)
- Adding a new service in server.py lifespan (lazy init, fails silently if cache dir missing)

No existing behavior is modified. No existing tests are affected. No existing imports change.

### 3. Conflicts with In-Progress Sprint Work?

**None.** Sprint 31A is running parameter sweeps in BacktestEngine — completely disjoint from this work. Zero file overlap.

### 4. Decision Log Impact?

No existing decisions changed. No new DECs anticipated — this follows established patterns:
- Config-gating (DEC-300 pattern)
- Separate service with lazy init (VIXDataService pattern from Sprint 27.9)
- JWT-protected REST endpoints (DEC-102, DEC-351)

### 5. Planned Work Adjustments?

None. This slots between 31A and 30 in the build track. Sprint 31.5 (Parallel Sweep Infrastructure) gains a pre-filter utility it can use but doesn't depend on.

---

## Implementation Prompt

```
# Sprint 31A.5, Session 1: Historical Query Layer (DuckDB Phase 1)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - CLAUDE.md
   - docs/project-knowledge.md (Current State, Architecture sections)
   - argus/data/vix_data_service.py (reference pattern for service structure)
   - argus/data/vix_config.py (reference pattern for config model)
   - argus/core/config.py (SystemConfig — where to add new config field)
   - argus/api/server.py (lifespan function — where to register new service)
2. Run the test baseline (DEC-328):
   Full suite: python -m pytest tests/ -x -q -n auto && cd ui && npx vitest run 2>&1 | tail -20
   Expected: ~4,674 pytest + ~846 Vitest, all passing
3. Verify you are on the correct branch: main (or current working branch)
4. Verify DuckDB is available: pip install duckdb --break-system-packages
   If not installable, halt and escalate — this is the sole external dependency.

## Objective
Add a DuckDB-based historical query service that provides SQL access to ARGUS's
existing Parquet cache (data/databento_cache/). This is a read-only analytical
layer — it never modifies the cache. Includes config-gated service, CLI tool,
REST endpoints, and a pre-filter utility method for future ExperimentRunner use.

## Requirements

### Config Model
1. Create `argus/data/historical_query_config.py`:
   - `HistoricalQueryConfig(BaseModel)` with fields:
     - `enabled: bool = False`
     - `cache_dir: str = "data/databento_cache"`
     - `max_memory_mb: int = 2048` (DuckDB memory limit)
     - `default_threads: int = 4` (DuckDB thread count)
   - Standard Pydantic validation (cache_dir non-empty, max_memory > 0, threads > 0)

2. Wire into `SystemConfig` in `argus/core/config.py`:
   - Add `historical_query: HistoricalQueryConfig = HistoricalQueryConfig()`
   - This makes it optional and disabled by default

3. Create `config/historical_query.yaml`:
   ```yaml
   historical_query:
     enabled: true
     cache_dir: "data/databento_cache"
     max_memory_mb: 2048
     default_threads: 4
   ```

4. Add `historical_query:` section to `config/system.yaml` and `config/system_live.yaml`:
   ```yaml
   historical_query:
     enabled: true
     cache_dir: "data/databento_cache"
     max_memory_mb: 2048
     default_threads: 4
   ```

### Core Service
5. Create `argus/data/historical_query_service.py`:

   ```python
   class HistoricalQueryService:
       """Read-only DuckDB query layer over the Parquet historical cache."""
   ```

   Constructor:
   - Accepts `config: HistoricalQueryConfig`
   - If `not config.enabled` or cache_dir doesn't exist: set `self._available = False`, log INFO, return
   - Initialize DuckDB in-memory connection with `SET memory_limit='{max_memory_mb}MB'` and `SET threads TO {threads}`
   - Create a VIEW over the cache: `CREATE VIEW historical AS SELECT * FROM read_parquet('{cache_dir}/**/*.parquet', union_by_name=true, hive_partitioning=false)`
   - If the VIEW creation fails (empty cache, bad files): set `_available = False`, log WARNING
   - Set `self._available = True`

   Properties:
   - `is_available: bool` — returns `self._available`

   Methods:
   - `query(sql: str, params: list | None = None) -> pd.DataFrame`:
     - Guards: if not available, raise `ServiceUnavailableError`
     - Executes SQL against the DuckDB connection, returns DataFrame
     - Wraps in try/except, logs errors, re-raises as `QueryExecutionError`
     - **Security:** This is for internal/CLI use. The REST endpoint uses
       parameterized templates, not raw SQL passthrough.

   - `get_symbol_bars(symbol: str, start_date: str, end_date: str) -> pd.DataFrame`:
     - Parameterized query: SELECT * FROM historical WHERE symbol = ? AND date >= ? AND date <= ? ORDER BY ts_event
     - Returns empty DataFrame if no data found

   - `get_available_symbols() -> list[str]`:
     - SELECT DISTINCT symbol FROM historical ORDER BY symbol
     - Cache result for 60s (simple TTL cache attribute)

   - `get_date_coverage(symbol: str | None = None) -> dict`:
     - If symbol: SELECT MIN(ts_event), MAX(ts_event), COUNT(*) FROM historical WHERE symbol = ?
     - If None: SELECT COUNT(DISTINCT symbol), MIN(ts_event), MAX(ts_event), COUNT(*) FROM historical
     - Returns dict with keys: symbol_count (if no symbol), min_date, max_date, bar_count

   - `validate_symbol_coverage(symbols: list[str], start_date: str, end_date: str, min_bars: int = 100) -> dict[str, bool]`:
     - For each symbol, checks bar count in date range >= min_bars
     - Returns dict mapping symbol -> passes_threshold
     - Designed for ExperimentRunner pre-filter (Sprint 31.5)
     - Batch query: SELECT symbol, COUNT(*) as bars FROM historical
       WHERE symbol IN (?, ?, ...) AND date >= ? AND date <= ?
       GROUP BY symbol

   - `get_cache_health() -> dict`:
     - Returns: total_symbols, date_range, total_bars, cache_dir, cache_size_bytes
     - cache_size_bytes from os.walk over cache_dir

   - `close()`:
     - Closes DuckDB connection if open

   Error classes (in same file or a small errors module):
   - `ServiceUnavailableError(Exception)` — service not initialized or cache missing
   - `QueryExecutionError(Exception)` — DuckDB query failed

   **IMPORTANT NOTES on Parquet schema:**
   - Databento OHLCV-1m Parquet files have specific column names. Before creating
     the VIEW, inspect one sample Parquet file's schema to determine actual column
     names (they may be `ts_event`, `symbol`, `open`, `high`, `low`, `close`,
     `volume`, or Databento-specific names like `rtype`, `publisher_id`, etc.).
   - Use `DESCRIBE SELECT * FROM read_parquet('{first_file}')` to discover the schema.
   - If column names differ from standard OHLCV, create the VIEW with aliases:
     `CREATE VIEW historical AS SELECT symbol, ts_event, open, high, low, close, volume, ... FROM read_parquet(...)`
   - Log the discovered schema at INFO level during init for operational visibility.

### Server Integration
6. In `argus/api/server.py` lifespan function:
   - After existing service initialization (follow the pattern of VIXDataService or similar):
   ```python
   # Historical Query Service
   if config.historical_query.enabled:
       from argus.data.historical_query_service import HistoricalQueryService
       historical_query_service = HistoricalQueryService(config.historical_query)
       if historical_query_service.is_available:
           logger.info("Historical Query Service initialized (DuckDB)")
       else:
           logger.warning("Historical Query Service enabled but cache unavailable")
   ```
   - Store on app state for route access (same pattern as other services)
   - Call `close()` in the shutdown section of lifespan

### REST Endpoints
7. Create `argus/api/routes/historical.py`:

   - `GET /api/v1/historical/symbols` (JWT-protected):
     - Returns: `{"symbols": [...], "count": N}`
     - 503 if service unavailable

   - `GET /api/v1/historical/coverage` (JWT-protected):
     - Optional query param: `symbol`
     - Returns: cache health dict (total_symbols, date_range, total_bars, cache_size_bytes)
     - If symbol specified: returns per-symbol coverage
     - 503 if service unavailable

   - `GET /api/v1/historical/bars/{symbol}` (JWT-protected):
     - Query params: `start_date`, `end_date` (both required, YYYY-MM-DD format)
     - Returns: OHLCV bars as JSON array
     - 400 if bad date format, 404 if symbol not found, 503 if service unavailable
     - Limit: max 50,000 bars per request (configurable)

   - `POST /api/v1/historical/validate-coverage` (JWT-protected):
     - Body: `{"symbols": [...], "start_date": "...", "end_date": "...", "min_bars": 100}`
     - Returns: `{"results": {"AAPL": true, "XYZ": false, ...}}`
     - 503 if service unavailable
     - This powers the ExperimentRunner pre-filter

   Register the router in server.py with the standard include pattern.

### CLI Tool
8. Create `scripts/query_cache.py`:
   - Standalone script (not imported by ARGUS runtime)
   - Accepts `--cache-dir` argument (default: `data/databento_cache`)
   - Accepts `--memory` argument (default: 2048 MB)
   - On startup: initializes DuckDB, creates VIEW, prints schema summary and basic stats
   - Interactive REPL loop using `readline` (with history support):
     - SQL queries → execute and print as formatted table (pandas .to_string())
     - `.schema` → show Parquet column schema
     - `.symbols` → list all symbols with count
     - `.coverage [SYMBOL]` → show date range and bar count
     - `.tables` → list available views
     - `.quit` / `.exit` / Ctrl+D → exit
     - `.help` → print available commands
   - Non-interactive mode: `--query "SELECT ..."` for scripting
   - Example usage in docstring:
     ```
     python scripts/query_cache.py
     python scripts/query_cache.py --cache-dir /Volumes/LaCie/argus-cache
     python scripts/query_cache.py --query "SELECT COUNT(DISTINCT symbol) FROM historical"
     ```

## Constraints
- Do NOT modify any existing strategy, backtest, or data service code
- Do NOT modify any frontend code
- Do NOT modify any existing test files
- Do NOT add DuckDB as a dependency for any existing component — it is only used
  by HistoricalQueryService and the CLI script
- The VIEW creation must handle the case where the cache directory is empty or
  contains no Parquet files — fail gracefully, not crash
- All queries are READ-ONLY. DuckDB connection should be opened in read-only
  mode if possible (DuckDB supports `duckdb.connect(read_only=True)` for
  file-based DBs; for in-memory, the Parquet files themselves are read-only)
- Do NOT store the DuckDB database to disk — always in-memory. The Parquet cache
  IS the persistent store.

## Test Targets
After implementation:
- Existing tests: all must still pass (unchanged)
- New tests to write:

  ### Service Tests (tests/data/test_historical_query_service.py):
  1. Test service initialization with valid config and mock Parquet directory
  2. Test service initialization with disabled config → is_available = False
  3. Test service initialization with missing cache_dir → is_available = False
  4. Test query() returns DataFrame for valid SQL
  5. Test query() raises ServiceUnavailableError when not available
  6. Test query() raises QueryExecutionError for invalid SQL
  7. Test get_symbol_bars() returns correct filtered data
  8. Test get_symbol_bars() returns empty DataFrame for unknown symbol
  9. Test get_available_symbols() returns sorted list
  10. Test get_date_coverage() with symbol filter
  11. Test get_date_coverage() without symbol filter (aggregate)
  12. Test validate_symbol_coverage() returns correct pass/fail per symbol
  13. Test validate_symbol_coverage() with min_bars threshold
  14. Test get_cache_health() returns expected keys
  15. Test close() idempotent

  ### Config Tests (tests/data/test_historical_query_config.py):
  16. Test HistoricalQueryConfig defaults
  17. Test config validation (max_memory > 0, threads > 0, cache_dir non-empty)
  18. Test config loads from YAML
  19. Config-YAML cross-validation: load historical_query.yaml, verify all keys
      recognized by HistoricalQueryConfig.model_fields

  ### API Tests (tests/api/test_historical_routes.py):
  20. Test GET /symbols returns list (service available)
  21. Test GET /symbols returns 503 (service unavailable)
  22. Test GET /coverage returns health dict
  23. Test GET /coverage with symbol param
  24. Test GET /bars/{symbol} with valid params
  25. Test GET /bars/{symbol} with bad date format → 400
  26. Test POST /validate-coverage returns per-symbol results
  27. Test all endpoints require JWT auth (401 without token)

  For Parquet test fixtures: create small test Parquet files (3-5 symbols, ~100
  bars each) in a temp directory during test setup. Use pyarrow or pandas to
  generate them. Do NOT use the actual production cache for tests.

- Minimum new test count: 25
- Test command: python -m pytest tests/data/test_historical_query_service.py tests/data/test_historical_query_config.py tests/api/test_historical_routes.py -x -q -v

## Config Validation
Write a test that loads config/historical_query.yaml and verifies all keys under
the historical_query section are recognized by HistoricalQueryConfig.

Expected mapping:
| YAML Key | Model Field |
|----------|-------------|
| enabled | enabled |
| cache_dir | cache_dir |
| max_memory_mb | max_memory_mb |
| default_threads | default_threads |

## Definition of Done
- [ ] HistoricalQueryService created with all methods
- [ ] HistoricalQueryConfig Pydantic model with validation
- [ ] Config YAML files created/updated
- [ ] Service wired into server.py lifespan (lazy init, config-gated)
- [ ] 4 REST endpoints created and registered
- [ ] CLI tool scripts/query_cache.py created with interactive and non-interactive modes
- [ ] All existing tests pass (unchanged)
- [ ] 25+ new tests written and passing
- [ ] Config validation test passing
- [ ] duckdb added to requirements.txt / pyproject.toml
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing services unaffected | All existing pytest tests pass |
| Server starts without historical_query config | Set enabled: false, start server, verify no errors |
| Server starts without cache directory | Remove/rename cache_dir, start server, verify graceful degradation |
| No import-time DuckDB dependency | grep -r "import duckdb" argus/ should only appear in historical_query_service.py |
| SystemConfig backward-compatible | Existing config files without historical_query section still load |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-31A.5/session-1-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The close-out report path: docs/sprints/sprint-31A.5/session-1-closeout.md
2. The diff range: git diff main...HEAD (or appropriate range)
3. The test command: python -m pytest tests/ -x -q -n auto && cd ui && npx vitest run 2>&1 | tail -20
4. Files that should NOT have been modified: any file under argus/strategies/, argus/backtest/, argus/intelligence/, argus/analytics/, ui/src/

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-31A.5/session-1-review.md

## Session-Specific Review Focus (for @reviewer)
1. Verify DuckDB connection is read-only — no write operations to the Parquet cache
2. Verify service degrades gracefully when cache_dir is missing or empty
3. Verify REST endpoints return 503 (not 500) when service unavailable
4. Verify no raw SQL passthrough from REST endpoints — only parameterized/template queries
5. Verify CLI tool handles Ctrl+C and Ctrl+D gracefully
6. Verify DuckDB import is lazy (only in historical_query_service.py, not at module top-level of server.py)
7. Verify SystemConfig still loads correctly without historical_query in YAML (backward compat)
8. Verify test Parquet fixtures are created in temp directories and cleaned up

## Sprint-Level Regression Checklist (for @reviewer)
| Check | How to Verify |
|-------|---------------|
| All existing tests pass | Full suite: pytest + vitest |
| No existing files modified beyond server.py and config.py | Check diff |
| Server startup works with feature disabled | config enabled: false |
| No new dependencies beyond duckdb | Check requirements changes |

## Sprint-Level Escalation Criteria (for @reviewer)
- ESCALATE if: existing test failures introduced
- ESCALATE if: DuckDB writes to Parquet cache files
- ESCALATE if: REST endpoint accepts raw SQL from clients
- ESCALATE if: service initialization blocks server startup (must be non-blocking)
```

---

## Fallback Tier 2 Review Prompt

```
# Tier 2 Review: Sprint 31A.5, Session 1

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):
docs/sprints/sprint-31A.5/session-1-review.md

## Tier 1 Close-Out Report
Read the close-out report from:
docs/sprints/sprint-31A.5/session-1-closeout.md

## Review Scope
- Diff to review: git diff main...HEAD (or appropriate range)
- Test command: python -m pytest tests/ -x -q -n auto && cd ui && npx vitest run 2>&1 | tail -20
- Files that should NOT have been modified: anything under argus/strategies/,
  argus/backtest/, argus/intelligence/, argus/analytics/, ui/src/

## Session-Specific Review Focus
1. Verify DuckDB connection is read-only — no write operations to the Parquet cache
2. Verify service degrades gracefully when cache_dir is missing or empty
3. Verify REST endpoints return 503 (not 500) when service unavailable
4. Verify no raw SQL passthrough from REST endpoints — only parameterized/template queries
5. Verify CLI tool handles Ctrl+C and Ctrl+D gracefully
6. Verify DuckDB import is lazy (only in historical_query_service.py)
7. Verify SystemConfig backward-compatible without historical_query in YAML
8. Verify test Parquet fixtures use temp directories and clean up
```
