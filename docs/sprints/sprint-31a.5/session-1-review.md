# Sprint 31A.5, Session 1 — Tier 2 Review Report
**Historical Query Layer (DuckDB Phase 1)**
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-03

---BEGIN-REVIEW---

## 1. Diff Summary

Two commits reviewed (`f912f4c` and `da6db0a`): 16 files changed, +1,942 lines, 0 deletions from existing code. 8 new source/test/config files, 7 modified files (additive only), 1 close-out report.

## 2. Spec Compliance

All requirements from the sprint package are satisfied:

| Requirement | Verdict |
|-------------|---------|
| `HistoricalQueryConfig` with 4 fields + validators | PASS |
| Wired into `SystemConfig` with `default_factory` | PASS |
| `config/historical_query.yaml` + system YAML sections | PASS |
| `HistoricalQueryService` with 6 query methods + 2 exceptions | PASS |
| Server lifespan lazy init (config-gated) | PASS |
| `close()` in shutdown path | PASS |
| `AppState.historical_query_service` field | PASS |
| 4 JWT-protected REST endpoints | PASS |
| 503 on unavailable (not 500) | PASS |
| Router registered in `routes/__init__.py` | PASS |
| `scripts/query_cache.py` REPL + dot-commands + --query | PASS |
| `duckdb` in `pyproject.toml` | PASS |
| >= 25 new tests | PASS (50 delivered) |
| No forbidden files modified | PASS |

## 3. Review Focus Items

### F1: DuckDB read-only — no writes to Parquet cache
**PASS.** The DuckDB connection is `:memory:` only. The sole operations on Parquet files are `read_parquet()` within a `CREATE VIEW` statement and `DESCRIBE`. No `INSERT`, `UPDATE`, `DELETE`, or `CREATE TABLE` statements target any Parquet files or persistent store. The service creates a VIEW (a virtual mapping), not a materialized copy.

### F2: Graceful degradation when cache_dir missing or empty
**PASS.** Four distinct degradation paths are handled: (1) `enabled=false` in config, (2) cache directory does not exist, (3) cache directory exists but contains no Parquet files, (4) DuckDB import fails. All set `_available = False` and log appropriately. Tests cover all four cases.

### F3: REST endpoints return 503 (not 500) when unavailable
**PASS.** The `_get_service()` helper raises `HTTPException(503)` when the service is `None` or `not is_available`. Each endpoint also catches `ServiceUnavailableError` and re-raises as 503. Tests verify 503 for all four endpoints.

### F4: No raw SQL passthrough from REST endpoints
**PASS.** All four REST endpoints call parameterized template methods (`get_available_symbols`, `get_cache_health`, `get_date_coverage`, `get_symbol_bars`, `validate_symbol_coverage`). No endpoint accepts or forwards SQL strings from clients. The `query()` method exists for internal/CLI use only and is explicitly documented as such.

### F5: CLI handles Ctrl+C and Ctrl+D
**PASS.** The REPL loop in `scripts/query_cache.py` catches `EOFError` (Ctrl+D, line 249) to break the loop and `KeyboardInterrupt` (Ctrl+C, line 251) to continue. Both are handled gracefully.

Note: The REPL uses `while True:` (line 246), which conflicts with CLAUDE.md's "No `while(true)` loops" code standard. However, this is a standard REPL pattern with clear exit conditions (`.quit`, `.exit`, EOFError, KeyboardInterrupt), so this is a pragmatic choice rather than an oversight.

### F6: DuckDB import is lazy
**PASS.** `import duckdb` appears only inside `HistoricalQueryService.__init__()` (line 96 of `historical_query_service.py`) and inside `scripts/query_cache.py`. It does not appear at module top-level in `server.py`, `config.py`, `dependencies.py`, `routes/__init__.py`, or `historical.py`. Verified by grep.

### F7: SystemConfig backward compatibility without `historical_query` in YAML
**PASS.** `SystemConfig.historical_query` uses `Field(default_factory=HistoricalQueryConfig)`, and `HistoricalQueryConfig()` defaults to `enabled=False`. Verified by instantiating `SystemConfig()` with no arguments -- it loads successfully with `historical_query.enabled = False`.

### F8: Test Parquet fixtures use temp directories
**PASS.** All service tests use `pytest`'s `tmp_path` fixture. The `cache_dir` fixture creates Parquet files under `tmp_path` which is automatically cleaned up by pytest. No production cache paths are accessed.

## 4. Findings

### F1 (LOW): `_get_service` missing return type annotation
`historical.py` line 25: `def _get_service(state: AppState):` has no return type annotation and uses `# type: ignore[return]`. Per project code style rules, all functions must have complete type hints. This is a minor gap since the function is internal to the routes module.

### F2 (LOW): `validate_coverage` endpoint uses `dict` body instead of Pydantic model
`historical.py` line 201: `body: dict = Body(...)` accepts an untyped dict. Project convention prefers Pydantic models for structured request bodies (per CLAUDE.md: "Use dataclasses or Pydantic models for structured data, not raw dicts"). This means request validation relies on manual checks (lines 219-231) rather than declarative Pydantic validation.

### F3 (LOW): `while True` in CLI REPL
`scripts/query_cache.py` line 246 uses `while True:`, which conflicts with CLAUDE.md's "No `while(true)` loops" rule. The loop has clear exit conditions via `.quit`/`.exit` commands and EOFError/KeyboardInterrupt handlers, making this a standard REPL pattern. Flagging for completeness but not a functional concern.

### F4 (LOW): `os.walk` and `os.path.getsize` in `get_cache_health` instead of `pathlib`
`historical_query_service.py` lines 390-395 use `os.walk` and `os.path.getsize` instead of `pathlib`, which is the project convention (CLAUDE.md: "Use pathlib for file paths, not os.path"). This is the only use of `os.walk`/`os.path` in the new files; the rest correctly uses `pathlib`.

### F5 (INFO): Close-out test delta discrepancy
The close-out report states +122 tests (4689 to 4811) but attributes only 50 new tests to this session. The discrepancy (+72) is explained as pre-existing uncommitted test work in `test_runner.py`. This is consistent with the git status shown at session start (test_runner.py was already modified). Full suite verified at 4811 passed.

## 5. Regression Check

| Check | Result |
|-------|--------|
| Full pytest suite (excl. test_main.py) | 4,811 passed, 0 failed |
| No forbidden directories modified | PASS (grep confirms no changes to strategies/, backtest/, intelligence/, analytics/, ui/) |
| No new dependencies beyond duckdb | PASS (only `duckdb>=1.0,<2` added to pyproject.toml) |
| Session-specific tests | 50/50 passed (3.90s) |

## 6. Escalation Criteria Evaluation

| Criterion | Triggered? |
|-----------|------------|
| Existing test failures introduced | NO — 4,811 passed, 0 failed |
| DuckDB writes to Parquet cache | NO — `:memory:` connection, VIEW only, no write operations |
| REST endpoint accepts raw SQL | NO — all endpoints use parameterized template methods |
| Service initialization blocks server startup | NO — lazy import, config-gated, exception-wrapped |

No escalation criteria triggered.

## 7. Verdict

**CLEAR.** The implementation is clean, well-tested, and fully compliant with the sprint spec. All 8 review focus items pass. The 4 low-severity findings (missing type annotation, raw dict body, while-true REPL, os.path usage) are minor code style deviations that do not affect functionality, security, or correctness. No regressions, no forbidden files touched, no escalation criteria triggered.

---END-REVIEW---

```json:structured-verdict
{
  "sprint": "31A.5",
  "session": 1,
  "title": "Historical Query Layer (DuckDB Phase 1)",
  "reviewer": "Tier 2 Automated Review",
  "date": "2026-04-03",
  "verdict": "CLEAR",
  "findings": [
    {
      "id": "F1",
      "severity": "LOW",
      "description": "_get_service() in historical.py missing return type annotation",
      "location": "argus/api/routes/historical.py:25"
    },
    {
      "id": "F2",
      "severity": "LOW",
      "description": "validate-coverage endpoint uses raw dict body instead of Pydantic model",
      "location": "argus/api/routes/historical.py:201"
    },
    {
      "id": "F3",
      "severity": "LOW",
      "description": "while True loop in CLI REPL (standard pattern but conflicts with code style rule)",
      "location": "scripts/query_cache.py:246"
    },
    {
      "id": "F4",
      "severity": "LOW",
      "description": "os.walk/os.path.getsize used instead of pathlib convention",
      "location": "argus/data/historical_query_service.py:390-395"
    },
    {
      "id": "F5",
      "severity": "INFO",
      "description": "Close-out test delta +122 vs +50 new tests explained by pre-existing uncommitted test_runner.py changes"
    }
  ],
  "escalation_triggers": [],
  "tests_passed": 4811,
  "tests_failed": 0,
  "new_tests": 50,
  "regressions": 0
}
```
