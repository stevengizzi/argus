# Sprint 27.7, Session 2: CounterfactualStore + Config Layer

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/counterfactual.py` (Session 1 output — CounterfactualPosition, CounterfactualTracker, RejectionStage)
   - `argus/strategies/telemetry_store.py` (EvaluationEventStore — pattern reference for aiosqlite store)
   - `argus/intelligence/config.py` (existing Pydantic config models — CatalystConfig, QualityEngineConfig patterns)
   - `argus/core/config.py` (SystemConfig — where to add CounterfactualConfig field)
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   python -m pytest tests/intelligence/test_counterfactual.py tests/core/test_fill_model.py -x -q
   ```
   Expected: all passing (Session 1 close-out confirmed full suite)
3. Verify you are on branch `main` or `sprint-27.7`

## Objective
Build SQLite persistence for counterfactual positions (`data/counterfactual.db`) and the full configuration layer: Pydantic model, YAML config file, and wiring onto SystemConfig.

## Requirements

### 1. Create `argus/intelligence/counterfactual_store.py` — SQLite Persistence

1a. Define `CounterfactualStore` class following the `EvaluationEventStore` pattern (`argus/strategies/telemetry_store.py`):
    - aiosqlite connection to `data/counterfactual.db` (separate DB per DEC-345 pattern)
    - `async def initialize()` — create tables if not exist, enable WAL mode
    - `async def close()` — close connection

1b. Table schema `counterfactual_positions`:
    ```sql
    CREATE TABLE IF NOT EXISTS counterfactual_positions (
        position_id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        strategy_id TEXT NOT NULL,
        entry_price REAL NOT NULL,
        stop_price REAL NOT NULL,
        target_price REAL NOT NULL,
        time_stop_seconds INTEGER,
        rejection_stage TEXT NOT NULL,
        rejection_reason TEXT NOT NULL,
        quality_score REAL,
        quality_grade TEXT,
        regime_vector_snapshot TEXT,  -- JSON-serialized dict
        signal_metadata TEXT,  -- JSON-serialized dict
        opened_at TEXT NOT NULL,  -- ISO 8601
        closed_at TEXT,
        exit_price REAL,
        exit_reason TEXT,
        theoretical_pnl REAL,
        theoretical_r_multiple REAL,
        duration_seconds REAL,
        max_adverse_excursion REAL DEFAULT 0.0,
        max_favorable_excursion REAL DEFAULT 0.0,
        bars_monitored INTEGER DEFAULT 0
    );
    ```

1c. Indexes:
    ```sql
    CREATE INDEX IF NOT EXISTS idx_cf_opened_at ON counterfactual_positions(opened_at);
    CREATE INDEX IF NOT EXISTS idx_cf_strategy ON counterfactual_positions(strategy_id);
    CREATE INDEX IF NOT EXISTS idx_cf_stage ON counterfactual_positions(rejection_stage);
    CREATE INDEX IF NOT EXISTS idx_cf_symbol ON counterfactual_positions(symbol);
    ```

1d. Methods:
    - `async def write_open(position)` — INSERT on position open (exit fields NULL)
    - `async def write_close(position)` — UPDATE exit fields on position close
    - `async def query(*, start_date=None, end_date=None, strategy_id=None, rejection_stage=None, quality_grade=None, limit=1000) -> list[dict]` — flexible query with optional filters
    - `async def get_closed_positions(start_date, end_date, **filters) -> list[dict]` — convenience method for FilterAccuracy (Session 4)
    - `async def enforce_retention(retention_days)` — DELETE WHERE opened_at < (now - retention_days)
    - `async def count() -> int` — total record count (for health monitoring)

1e. Fire-and-forget writes: wrap write operations in try/except, log WARNING on failure. Counterfactual data loss is acceptable for individual records but should be visible in logs (unlike evaluation telemetry which silently drops). Rate-limit warnings to 1 per 60 seconds to avoid log spam.

### 2. Create `config/counterfactual.yaml` — Default Configuration

```yaml
# Counterfactual Engine (Sprint 27.7)
# Tracks theoretical outcomes of rejected signals for filter accuracy analysis.
# Config-gated: set enabled: false to disable entirely (zero overhead).

counterfactual:
  enabled: true
  retention_days: 90
  no_data_timeout_seconds: 300
  eod_close_time: "16:00"
```

### 3. Add `CounterfactualConfig` to `argus/intelligence/config.py`

```python
class CounterfactualConfig(BaseModel):
    """Configuration for the Counterfactual Engine (Sprint 27.7)."""
    enabled: bool = True
    retention_days: int = 90
    no_data_timeout_seconds: int = 300
    eod_close_time: str = "16:00"
```

Add this alongside the existing `CatalystConfig`, `QualityEngineConfig` models.

### 4. Wire onto `argus/core/config.py` — SystemConfig

Add to `SystemConfig`:
```python
counterfactual: CounterfactualConfig = Field(default_factory=CounterfactualConfig)
```

Import `CounterfactualConfig` from `argus.intelligence.config`.

## Constraints
- Do NOT modify: `argus/main.py` (startup wiring comes in S3b), `argus/intelligence/startup.py` (factory method comes in S3b), `argus/core/events.py` (event type comes in S3a), any strategy files, any frontend files
- Do NOT add: `counterfactual` section to `config/system.yaml` or `config/system_live.yaml` (deferred to S3b to keep this session's modified file count at 13)
- Store must use `data/counterfactual.db` — NOT `data/argus.db`
- Follow the exact Pydantic field names listed in the config table. Pydantic silently drops unrecognized keys.

## Config Validation
Write a test that loads `config/counterfactual.yaml` and verifies all keys under `counterfactual` are recognized by `CounterfactualConfig`:
1. Load YAML and extract `counterfactual` section keys
2. Compare against `CounterfactualConfig.model_fields.keys()`
3. Assert no YAML keys absent from model

Expected mapping:
| YAML Key | Model Field |
|----------|-------------|
| `enabled` | `enabled` |
| `retention_days` | `retention_days` |
| `no_data_timeout_seconds` | `no_data_timeout_seconds` |
| `eod_close_time` | `eod_close_time` |

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **store: initialize creates table** — initialize() creates counterfactual_positions table and indexes
  2. **store: write_open persists** — write open position, query returns it with exit fields NULL
  3. **store: write_close updates** — write close, query returns updated exit fields
  4. **store: query by date range** — insert positions across dates, query with start/end returns correct subset
  5. **store: query by strategy** — filter by strategy_id
  6. **store: query by rejection_stage** — filter by stage
  7. **store: retention enforcement** — insert old records, enforce_retention deletes them, recent records survive
  8. **config: YAML → Pydantic validation** — config keys match model fields (see Config Validation above)
  9. **config: CounterfactualConfig on SystemConfig** — SystemConfig() has counterfactual field with correct defaults
  10. **config: enabled=false default factory** — CounterfactualConfig(enabled=False) correctly disables
- Minimum new test count: 8
- Test file: `tests/intelligence/test_counterfactual_store.py` and additions to `tests/intelligence/test_counterfactual.py` or `tests/test_config.py`
- Test command: `python -m pytest tests/intelligence/test_counterfactual_store.py tests/intelligence/test_counterfactual.py -x -q`

## Definition of Done
- [ ] `argus/intelligence/counterfactual_store.py` created with full CRUD and retention
- [ ] `config/counterfactual.yaml` created with documented defaults
- [ ] `CounterfactualConfig` added to `argus/intelligence/config.py`
- [ ] `counterfactual` field added to `SystemConfig` in `argus/core/config.py`
- [ ] Config validation test passing
- [ ] All existing tests pass
- [ ] ≥8 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| CounterfactualStore uses `data/counterfactual.db` | Grep store code for DB path — must not reference `argus.db` |
| SystemConfig defaults still work | Existing config loading tests pass — `SystemConfig()` constructs without error |
| CounterfactualConfig field names match YAML keys | Config validation test (see above) |
| No changes to `main.py` or `startup.py` | `git diff argus/main.py argus/intelligence/startup.py` shows no changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
`docs/sprints/sprint-27.7/session-2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.7/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.7/session-2-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/intelligence/test_counterfactual_store.py tests/intelligence/test_counterfactual.py tests/core/test_fill_model.py -x -q`
5. Files that should NOT have been modified: `argus/main.py`, `argus/intelligence/startup.py`, `argus/core/events.py`, any files in `argus/strategies/`, any files in `argus/ui/`, `config/system.yaml`, `config/system_live.yaml`

The @reviewer will write its report to:
`docs/sprints/sprint-27.7/session-2-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the post-review fix
documentation protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify store uses `data/counterfactual.db` — separate file, not argus.db
2. Verify WAL mode is enabled on the store connection
3. Verify retention enforcement deletes only by `opened_at` date, not other criteria
4. Verify CounterfactualConfig Pydantic field names match YAML keys exactly
5. Verify `SystemConfig.counterfactual` has `Field(default_factory=CounterfactualConfig)` — not a bare default
6. Verify fire-and-forget write pattern includes warning-level logging with rate limiting

## Sprint-Level Regression Checklist (for @reviewer)
(see review-context.md)

## Sprint-Level Escalation Criteria (for @reviewer)
(see review-context.md)
