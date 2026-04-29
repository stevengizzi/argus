# Sprint 31.915, Session 1: `evaluation.db` Retention Mechanism + Observability

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt. Pay particular attention to RULE-038 (structural-anchor verification), RULE-039 (non-bypassable validation), RULE-042 (silent-default anti-pattern), and RULE-050 (CI verification discipline).

2. Read these files to load context:
   - `docs/sprints/sprint-31.915-evaluation-db-retention/sprint-spec.md` — this session's full spec.
   - `argus/strategies/telemetry_store.py` — the file we're modifying.
   - `argus/data/migrations/evaluation.py` — the migration module we must NOT touch.
   - `tests/test_telemetry_store.py` — existing IMPROMPTU-10 lifecycle tests we append to but never modify.
   - `tests/strategies/test_telemetry_store_vacuum.py` — Sprint 31.8 VACUUM tests, regression-only.
   - `argus/core/health.py` — health framework we extend with `evaluation_db` subfield.
   - `argus/core/config.py` — Pydantic config tree we extend with `EvaluationStoreConfig`.
   - `config/system_live.yaml` and `config/system.yaml` — overlay structure for understanding DEC-384's standalone-overlay registry.
   - `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-c-closeout.md` — recent migration framework adoption (do not break).
   - The IMPROMPTU-10 closeout at `docs/sprints/sprint-31.9/IMPROMPTU-10-closeout.md` — the prior fix this builds on.

3. Run the test baseline (DEC-328):
   - **Session 1 of sprint** (full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`
   - Expected: 5,269 tests, all passing.

4. Verify you are on the correct branch: `main` (HITL-on-`main`).

5. **Run the structural-anchor grep-verify commands** from the "Files to Modify" section below. For each entry, run the verbatim grep-verify command and confirm the anchor still resolves to the expected location. If drift is detected, disclose under RULE-038 in the close-out and proceed against the actual structural anchors. If the anchor is not found at all, HALT and request operator disposition rather than guess.

6. Verify the pre-condition state:
   ```bash
   ls -la data/evaluation.db data/evaluation.db-wal data/evaluation.db-shm 2>&1
   # Expected: all three "No such file or directory" — operator deleted them post-investigation.
   df -h / | tail -1
   # Expected: ≥15 Gi free.
   ps -axo pid,etime,command | grep -E "argus\.main|uvicorn argus" | grep -v grep
   # Expected: empty output — ARGUS is down.
   ```
   If any of these are not as expected, HALT.

## Objective

Diagnose and fix the silent-failure mode in IMPROMPTU-10's periodic retention task, lower `RETENTION_DAYS` default to 2 via a new config-driven `EvaluationStoreConfig` Pydantic model, add operational visibility (always-log retention iterations + `/health` endpoint subfields), add a chicken-and-egg-safe pre-VACUUM disk-headroom check, and write an operator runbook covering reclaim procedures.

## Phase A — Instrumented Diagnostic (REQUIRED BEFORE PHASE B)

Goal: produce conclusive evidence of why `cleanup_old_events()` did not log `retention deleted N rows` on the Apr 27→28 retention iteration that demonstrably freed pages (freelist transitioned 0.0% → 0.9%).

### A1. Create `scripts/diag_retention_logging.py`

Write a focused isolation script — NOT a pytest test. The script must:

1. Use `tempfile.NamedTemporaryFile(suffix=".db", delete=False)` for the DB path.
2. Construct an `EvaluationEventStore(db_path=tmp_path)` and `await store.initialize()`.
3. Insert ~100 rows via direct `await store._conn.execute(...)` with `trading_date = (datetime.now(_ET) - timedelta(days=10)).strftime("%Y-%m-%d")` — clearly outside the default 7-day retention window.
4. Capture `PRAGMA freelist_count` and `PRAGMA page_count` before calling `cleanup_old_events()`.
5. Patch `cleanup_old_events` (or add temporary `print()` statements via monkeypatch) to expose:
   - The cutoff string computed.
   - The cursor's `rowcount` value **immediately after `await self._conn.execute(...)` and BEFORE `await self._conn.commit()`**.
   - The cursor's `rowcount` value **immediately after `await self._conn.commit()`**.
   - Whether `if deleted > 0:` evaluated true or false.
   - Whether `_vacuum()` was invoked.
   - Any exception raised.
6. Capture `PRAGMA freelist_count` and `PRAGMA page_count` after.
7. Use the actual production logger configuration — import and configure logging the same way `argus/core/logging_config.py` does, NOT pytest caplog. The point is to reproduce production logger routing.
8. Repeat steps 3–6 with `trading_date = (datetime.now(_ET) + timedelta(days=1)).strftime("%Y-%m-%d")` (clearly INSIDE retention) to confirm the zero-deletion path.
9. Print all captured values to stdout in a structured table.
10. Clean up the tempfile at script end.

Run with: `python scripts/diag_retention_logging.py 2>&1 | tee dev-logs/2026-04-28_retention-mechanism-diagnostic.md`.

### A2. Document findings

Write `dev-logs/2026-04-28_retention-mechanism-diagnostic.md` (the redirected output from A1, plus a synthesis section):

```markdown
# Retention Mechanism Diagnostic — 2026-04-28

## Hypothesis tree (from sprint-spec)
- H1: aiosqlite cursor.rowcount returns 0 post-commit
- H2: Logger config issue
- H3: Exception eaten by _run_periodic_retention's broad except
- H4: Something else

## Raw evidence
[paste structured table from script output]

## Confirmed root cause
[H1 / H2 / H3 / H4]

## Mechanism
[2–3 sentences explaining exactly why the production code's log line did not fire on Apr 27→28]

## Fix shape (Phase B)
[1–2 sentences: what code change addresses the mechanism]
```

### A3. Halt-or-proceed gate

If the script confirms H1 (rowcount=0 post-commit, rowcount>0 pre-commit, with rows actually deleted on disk), proceed to Phase B with the H1 fix.

If the script confirms H2 or H3 with a clear mechanism, proceed to Phase B with the corresponding fix.

If the script's findings are H4 ("something else") or are inconclusive, HALT and write the diagnostic findings file with status INCONCLUSIVE; surface to operator for next-step disposition. Do NOT proceed to Phase B with a guess.

### A4. Delete the diagnostic script

After Phase A completes, **delete `scripts/diag_retention_logging.py`**. It is single-use; the regression test in Phase C captures the mechanism for future sessions. The diagnostic findings file at `dev-logs/2026-04-28_retention-mechanism-diagnostic.md` remains as the authoritative-record artifact.

## Phase B — Implementation

### Files to Modify

#### 1. `config/evaluation_store.yaml` (NEW FILE)

Edit shape: creation.

Content:

```yaml
# data/evaluation.db retention + observability policy.
# Sprint 31.915 — supersedes implicit DEF-197 closure constants (DEC-389).

evaluation_store:
  # Retention: how many ET trading days of evaluation_events to keep.
  # Lowered from 7 (IMPROMPTU-10 default) to 2 per DEC-389; aligns steady-state
  # ~10 GB with the operator's disk environment. Range: [1, 30].
  retention_days: 2

  # Periodic retention task cadence in seconds. Default 4 hours = 14400.
  retention_interval_seconds: 14400

  # Startup-reclaim VACUUM gates: only triggers when the DB exceeds
  # startup_reclaim_min_size_mb AND freelist ratio exceeds
  # startup_reclaim_freelist_ratio.
  startup_reclaim_min_size_mb: 500
  startup_reclaim_freelist_ratio: 0.5

  # WARNING threshold for post-init size check.
  size_warning_threshold_mb: 2000

  # Pre-VACUUM disk-headroom safety. VACUUM is aborted (with WARNING) if
  # free disk space on the volume is less than headroom_multiplier × current
  # DB size. Default 2.0 — VACUUM INTO temp-copy can reach 2× source size.
  pre_vacuum_headroom_multiplier: 2.0
```

Pre-flight grep-verify: `test -f config/evaluation_store.yaml; echo "exists=$?"` — expected `exists=1` (file does not yet exist).

#### 2. `argus/core/config.py` — add `EvaluationStoreConfig` Pydantic model

Anchor: top-level config models (search for `class TelemetryConfig` or other adjacent telemetry/data config classes — pick the section where infrastructure-tier config models live).

Edit shape: insertion of a new Pydantic model class + registration in `_STANDALONE_SYSTEM_OVERLAYS` per DEC-384.

Pre-flight grep-verify:
```bash
grep -n "_STANDALONE_SYSTEM_OVERLAYS" argus/core/config.py
# Expected: ≥1 hit. (Directional only — DEC-384 / FIX-01 anchored this name.)
grep -n "class .*Config(BaseModel)" argus/core/config.py | head
# Expected: multiple hits showing the existing pattern to follow.
```

The new model:

```python
class EvaluationStoreConfig(BaseModel):
    """Retention + observability policy for ``data/evaluation.db`` (DEC-389)."""

    retention_days: int = Field(default=2, ge=1, le=30)
    retention_interval_seconds: int = Field(default=4 * 60 * 60, ge=60)
    startup_reclaim_min_size_mb: int = Field(default=500, ge=1)
    startup_reclaim_freelist_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    size_warning_threshold_mb: int = Field(default=2000, ge=1)
    pre_vacuum_headroom_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)

    model_config = ConfigDict(extra="forbid")
```

Register in `_STANDALONE_SYSTEM_OVERLAYS` so `config/evaluation_store.yaml` is deep-merged via the standalone-overlay path (the same pattern DEC-384 / FIX-01 established for `config/quality_engine.yaml`). Read the existing entry for `quality_engine` and mirror it.

If the model needs to be exposed on the system root: add `evaluation_store: EvaluationStoreConfig = Field(default_factory=EvaluationStoreConfig)` to whichever Pydantic class represents the system config root (search for where `quality_engine` is exposed — same place).

#### 3. `argus/strategies/telemetry_store.py` — config-driven, observability fixes, pre-VACUUM check

Anchor: `class EvaluationEventStore`. Pre-flight grep-verify:
```bash
grep -n "class EvaluationEventStore" argus/strategies/telemetry_store.py
# Expected: 1 hit at line 38 (directional).
grep -n "RETENTION_DAYS: int = 7" argus/strategies/telemetry_store.py
# Expected: 1 hit. (We are removing this hardcoded class constant.)
grep -n "apply_migrations" argus/strategies/telemetry_store.py
# Expected: 1 hit. (We are NOT modifying this line — RULE-038.)
```

Edit shapes (in order):

**3a.** Replace the class constants block with instance fields populated from a new `EvaluationStoreConfig` parameter to `__init__`:

```python
def __init__(
    self,
    db_path: str,
    config: EvaluationStoreConfig | None = None,
) -> None:
    """Initialize the store.

    Args:
        db_path: Path to the SQLite database file.
        config: Retention + observability policy. If None, defaults to
            EvaluationStoreConfig() (RETENTION_DAYS=2, etc.) per DEC-389.
    """
    self._db_path = db_path
    self._config = config or EvaluationStoreConfig()
    self._conn: aiosqlite.Connection | None = None
    self._last_warning_time: float = 0.0
    self._retention_task: asyncio.Task[None] | None = None
    # G5: observability state for /health subfield
    self._last_retention_run_at_et: datetime | None = None
    self._last_retention_deleted_count: int | None = None
```

Replace every reference to `self.RETENTION_DAYS` with `self._config.retention_days`, `self.RETENTION_INTERVAL_SECONDS` with `self._config.retention_interval_seconds`, etc.

Keep the class constants as DEPRECATED aliases that read from `_config` only if absolutely required for backward compat with existing tests that monkeypatch them (e.g., `test_periodic_retention_invokes_cleanup_old_events` monkeypatches `RETENTION_INTERVAL_SECONDS`). Preferred path: change those tests to use `store._config.retention_interval_seconds = ...`. **HALT and ask operator before deviating from this preferred path.**

Note: the existing IMPROMPTU-10 test `test_periodic_retention_invokes_cleanup_old_events` at `tests/test_telemetry_store.py:220` monkeypatches `RETENTION_INTERVAL_SECONDS = 0.05`. This is the ONLY existing test we are permitted to surgically adapt — change the monkeypatch target from the class constant to `store._config.retention_interval_seconds = 0.05`. Do this as a one-line edit, treat it as a regression-preserving accommodation, and call it out explicitly in the closeout's "Judgment Calls" section.

**3b.** Apply the Phase-A-confirmed root-cause fix to `cleanup_old_events()`:

If H1 (rowcount-after-commit): capture `deleted = cursor.rowcount` IMMEDIATELY after `await self._conn.execute(...)` and BEFORE `await self._conn.commit()`.

```python
async def cleanup_old_events(self) -> None:
    """..."""
    if self._conn is None:
        return
    cutoff = (datetime.now(_ET) - timedelta(days=self._config.retention_days)).strftime("%Y-%m-%d")
    size_before_mb = self._get_db_size_mb()
    cursor = await self._conn.execute(
        "DELETE FROM evaluation_events WHERE trading_date < ?",
        (cutoff,),
    )
    deleted = cursor.rowcount  # G1 fix: capture BEFORE commit (DEF-231)
    await self._conn.commit()

    # G5: record observability state regardless of branch
    self._last_retention_run_at_et = datetime.now(_ET)
    self._last_retention_deleted_count = deleted

    # G3: always log, both branches
    if deleted > 0 and self._config.retention_days > 0 and self.VACUUM_AFTER_CLEANUP:
        await self._vacuum()
        size_after_mb = self._get_db_size_mb()
        logger.info(
            "EvaluationEventStore: retention deleted %d rows (before %s), "
            "db size %.1f MB -> %.1f MB (freed %.1f MB)",
            deleted, cutoff, size_before_mb, size_after_mb, size_before_mb - size_after_mb,
        )
    elif deleted > 0:
        logger.info("EvaluationEventStore: retention deleted %d rows (before %s)", deleted, cutoff)
    else:
        logger.info(
            "EvaluationEventStore: retention scanned (cutoff %s, 0 rows matched)",
            cutoff,
        )  # G3: zero-deletion path now logged
```

(`VACUUM_AFTER_CLEANUP` remains a class constant — it's a behavioral toggle, not an operator-tunable value. If Phase A finds a different root cause, adapt the fix shape to match; the observability behavior is unchanged.)

**3c.** Add G4 — pre-VACUUM disk-headroom check inside `_vacuum()`:

```python
async def _vacuum(self) -> None:
    """..."""
    if self._conn is None:
        return

    # G4: pre-VACUUM disk-headroom check (DEF-232).
    # VACUUM INTO requires ~2× source-size temporary space on the same volume.
    # If we proceed under disk pressure, we get a silent ENOSPC inside the
    # broad except in _run_periodic_retention. Refuse loudly instead.
    import shutil
    db_size = Path(self._db_path).stat().st_size if Path(self._db_path).exists() else 0
    free_bytes = shutil.disk_usage(Path(self._db_path).parent).free
    required = int(db_size * self._config.pre_vacuum_headroom_multiplier)
    if free_bytes < required:
        logger.warning(
            "EvaluationEventStore: pre-VACUUM headroom check FAILED "
            "(free=%.1f MB, required=%.1f MB at %.1fx multiplier, db=%.1f MB) "
            "— aborting this VACUUM cycle. See docs/operations/evaluation-db-runbook.md.",
            free_bytes / (1024 * 1024),
            required / (1024 * 1024),
            self._config.pre_vacuum_headroom_multiplier,
            db_size / (1024 * 1024),
        )
        return  # abort cycle; retention DELETE has already committed

    # ...rest of _vacuum() unchanged (close → sync VACUUM → reopen)...
```

**3d.** Add G5 helper for the health subfield:

```python
def get_health_snapshot(self) -> dict[str, object]:
    """Return current health/observability state for /health endpoint (G5)."""
    size_mb = self._get_db_size_mb()
    last_run = self._last_retention_run_at_et
    return {
        "size_mb": round(size_mb, 1),
        "last_retention_run_at_et": last_run.isoformat() if last_run else None,
        "last_retention_deleted_count": self._last_retention_deleted_count,
        # freelist_pct is computed lazily — async, must be awaited by caller
    }

async def get_freelist_pct(self) -> float:
    """Async sibling for /health (computes freelist ratio)."""
    return await self._get_freelist_ratio() * 100.0
```

#### 4. `argus/main.py` — wire config into store construction

Anchor: `[10.3/12] Initializing telemetry store...` block. Pre-flight grep-verify:
```bash
grep -n "EvaluationEventStore(eval_db_path)" argus/main.py
# Expected: 1 hit at line 938 (directional).
grep -n "EvaluationEventStore" argus/main.py
# Expected: 2-3 hits (import + construct + cleanup_old_events call).
```

Edit shape: change the construction call from:

```python
self._eval_store = EvaluationEventStore(eval_db_path)
```

to:

```python
self._eval_store = EvaluationEventStore(
    eval_db_path,
    config=config.evaluation_store,
)
```

And register the store with the health monitor for the new subfield (place after the existing `update_component("evaluation_store", ComponentStatus.HEALTHY)` line, or use whatever the established pattern is — read `argus/core/health.py` first to confirm idiom).

#### 5. `argus/api/server.py` — wire config into alternate init path

Anchor: same pattern, `cleanup_old_events()` site at `argus/api/server.py:331`. Pre-flight grep-verify:
```bash
grep -n "EvaluationEventStore(db_path)" argus/api/server.py
# Expected: 1 hit (directional).
```

Edit shape: change the construction to pass `config=app_state.config.evaluation_store` if available, else `None` (for backward compat with the lifespan init when full config is not present).

#### 6. `argus/core/health.py` — add `evaluation_db` health subfield

Anchor: `class HealthMonitor` and the existing component-tracking pattern. Pre-flight grep-verify:
```bash
grep -n "class HealthMonitor" argus/core/health.py
# Expected: 1 hit (directional).
grep -n "update_component" argus/core/health.py
# Expected: multiple hits showing the existing API.
```

Edit shape: add a `register_evaluation_store(store: EvaluationEventStore)` method (or similar — read existing patterns first) that lets `HealthMonitor` query the store's `get_health_snapshot()` + `get_freelist_pct()` at health-endpoint-call time. Add the resulting fields to whichever existing endpoint method renders `/health` JSON.

The endpoint should expose:

```json
{
  "evaluation_db": {
    "size_mb": 1234.5,
    "last_retention_run_at_et": "2026-04-29T13:17:42-04:00",
    "last_retention_deleted_count": 19500000,
    "freelist_pct": 0.0
  }
}
```

If `last_retention_run_at_et` has never run yet (fresh boot), the field is `null` — frontend handles null gracefully.

## Phase C — Tests + Runbook + Closeout

### C1. New tests in `tests/test_telemetry_store.py` (APPEND ONLY)

Add at end of file. Do NOT modify the existing 3 IMPROMPTU-10 tests except for the `RETENTION_INTERVAL_SECONDS` monkeypatch surgical adaptation noted in Phase B.3a.

```python
# Sprint 31.915 — DEC-389 / DEF-231 / DEF-232 / DEF-233 / DEF-234 regression tests

async def test_retention_days_is_config_driven(tmp_path):
    """G2 / DEC-389: RETENTION_DAYS reflects config, not class constant."""
    from argus.core.config import EvaluationStoreConfig
    cfg = EvaluationStoreConfig(retention_days=3)
    store = EvaluationEventStore(str(tmp_path / "test.db"), config=cfg)
    await store.initialize()
    try:
        assert store._config.retention_days == 3
    finally:
        await store.close()


async def test_retention_logs_zero_deletion_path(tmp_path, caplog):
    """G3 / DEF-231: zero-deletion branch logs an INFO line."""
    import logging
    caplog.set_level(logging.INFO, logger="argus.strategies.telemetry_store")
    store = EvaluationEventStore(str(tmp_path / "test.db"))
    await store.initialize()
    try:
        await store.cleanup_old_events()  # empty DB → 0 deletions
        assert any(
            "0 rows matched" in rec.message
            for rec in caplog.records
        ), f"Expected zero-deletion INFO log; got: {[r.message for r in caplog.records]}"
    finally:
        await store.close()


async def test_retention_logs_success_path(tmp_path, caplog):
    """G3 + G1 regression / DEF-231: positive-deletion branch logs an INFO line.

    This is the regression guard against the IMPROMPTU-10 silent-failure mode.
    """
    import logging
    from argus.strategies.telemetry import EvaluationEvent, EvaluationEventType
    caplog.set_level(logging.INFO, logger="argus.strategies.telemetry_store")
    store = EvaluationEventStore(str(tmp_path / "test.db"))
    await store.initialize()
    try:
        # Insert a row 10 days old
        old_ts = datetime.now(_ET) - timedelta(days=10)
        old_event = EvaluationEvent(
            timestamp=old_ts,
            symbol="TEST",
            strategy_id="test_strategy",
            event_type=EvaluationEventType.ENTRY_EVALUATION,
            result="REJECTED",
            reason="diagnostic",
            metadata={},
        )
        await store.write_event(old_event)
        await store.cleanup_old_events()
        assert any(
            "retention deleted 1 rows" in rec.message or "deleted 1 rows" in rec.message
            for rec in caplog.records
        ), f"Expected success-path INFO log; got: {[r.message for r in caplog.records]}"
    finally:
        await store.close()


async def test_pre_vacuum_disk_headroom_check_aborts_when_insufficient(tmp_path, monkeypatch, caplog):
    """G4 / DEF-232: VACUUM aborts loudly when free disk < 2x DB size."""
    import logging
    import shutil
    caplog.set_level(logging.WARNING, logger="argus.strategies.telemetry_store")
    store = EvaluationEventStore(str(tmp_path / "test.db"))
    await store.initialize()
    try:
        # Mock disk_usage to return free=1 byte, total=huge, used=huge
        from collections import namedtuple
        DU = namedtuple("DU", "total used free")
        monkeypatch.setattr(shutil, "disk_usage", lambda p: DU(1_000_000_000, 999_999_999, 1))
        # Force a VACUUM call
        await store._vacuum()
        assert any(
            "headroom check FAILED" in rec.message
            for rec in caplog.records
        ), f"Expected pre-VACUUM headroom WARNING; got: {[r.message for r in caplog.records]}"
    finally:
        await store.close()


async def test_pre_vacuum_disk_headroom_check_proceeds_when_sufficient(tmp_path, monkeypatch):
    """G4 / DEF-232: VACUUM proceeds when free disk >= 2x DB size (happy path)."""
    import shutil
    store = EvaluationEventStore(str(tmp_path / "test.db"))
    await store.initialize()
    try:
        # disk_usage left at real value — tmp_path almost certainly has plenty of room
        # Just confirm no exception is raised and the connection is still alive after VACUUM
        await store._vacuum()
        assert store._conn is not None  # reconnected after VACUUM
    finally:
        await store.close()


async def test_get_health_snapshot_exposes_all_fields(tmp_path):
    """G5 / DEF-233: get_health_snapshot returns all required fields."""
    store = EvaluationEventStore(str(tmp_path / "test.db"))
    await store.initialize()
    try:
        snap = store.get_health_snapshot()
        assert "size_mb" in snap
        assert "last_retention_run_at_et" in snap  # null on fresh init
        assert "last_retention_deleted_count" in snap  # null on fresh init
        # freelist is async, separately queried
        freelist = await store.get_freelist_pct()
        assert isinstance(freelist, float)
        assert 0.0 <= freelist <= 100.0
    finally:
        await store.close()
```

If Phase A surfaced a different root cause than H1, add an additional test capturing that mechanism (test name reflects the mechanism).

### C2. New test in `tests/api/test_health.py` (APPEND ONLY)

Add at end of file:

```python
async def test_health_endpoint_exposes_evaluation_db_subfields(client):
    """Sprint 31.915 / DEF-233: /health surfaces evaluation_db state."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "evaluation_db" in body
    eval_db = body["evaluation_db"]
    assert "size_mb" in eval_db
    assert "last_retention_run_at_et" in eval_db
    assert "last_retention_deleted_count" in eval_db
    assert "freelist_pct" in eval_db
```

(Adapt the test fixture to whatever the existing `test_health.py` uses — `client`, `httpx.AsyncClient`, etc.)

### C3. Operator runbook at `docs/operations/evaluation-db-runbook.md` (NEW FILE)

Write a 2-page runbook with these sections:

```markdown
# Operator Runbook — `data/evaluation.db`

> Sprint 31.915 — supersedes IMPROMPTU-10 §7 documentation.

## What this DB is

[2 paragraphs: data flow, schema, who consumes it, retention policy.]

## Symptoms → diagnosis quick table

| Symptom | First check | Likely cause |
|---|---|---|
| `df -h /` < 5 GB free | `du -sh data/evaluation.db` | DB > steady-state target |
| `EvaluationEventStore: DB size N MB exceeds threshold` WARNING at boot | Check `RETENTION_DAYS` config | Operator-disk-environment mismatch |
| No `retention scanned (cutoff X, N rows matched)` INFO lines for >5 hours | Check `_run_periodic_retention` task is alive (`/health` evaluation_db.last_retention_run_at_et) | Task crashed silently (DEF-231 family) |
| `headroom check FAILED` WARNING | `df -h /` and check for FD-pinned deleted files via `lsof | grep -i evaluation.db` | Chicken-and-egg disk pressure |
| Disk recovers ~1 GB after `rm` of 25 GB file | `lsof | grep -i evaluation.db` | Process holding deleted-inode FD; kill the process |

## Diagnostic queries

\`\`\`bash
# Q1 — row count + date span
sqlite3 -readonly data/evaluation.db <<'EOF'
SELECT MIN(trading_date), MAX(trading_date), COUNT(*),
       COUNT(DISTINCT trading_date) AS distinct_days
FROM evaluation_events;
EOF

# Q2 — per-day distribution
sqlite3 -readonly data/evaluation.db <<'EOF'
SELECT trading_date, COUNT(*) FROM evaluation_events
GROUP BY trading_date ORDER BY trading_date DESC LIMIT 30;
EOF

# Q3 — file structure
sqlite3 -readonly data/evaluation.db <<'EOF'
PRAGMA page_count;
PRAGMA page_size;
PRAGMA freelist_count;
EOF
\`\`\`

## Reclaim procedure 1: `VACUUM INTO` (preferred when disk has headroom)

**Pre-condition:** `df -h /` shows free space ≥ 2× current `data/evaluation.db` size.

\`\`\`bash
# 1. Stop ARGUS cleanly
./scripts/stop_live.sh   # (or operator's preferred stop method)

# 2. Verify ARGUS is fully down
ps -axo pid,etime,command | grep -E "argus\.main|uvicorn argus" | grep -v grep
# Expected: empty.

# 3. Verify no FDs are pinning the file (Apr 28 incident)
lsof data/evaluation.db 2>&1 | head
# Expected: empty.

# 4. VACUUM INTO new file
sqlite3 data/evaluation.db <<'EOF'
VACUUM INTO 'data/evaluation.db.new';
EOF

# 5. Verify the new file
ls -l data/evaluation.db.new
sqlite3 -readonly data/evaluation.db.new "SELECT COUNT(*) FROM evaluation_events;"

# 6. Atomic swap
mv data/evaluation.db data/evaluation.db.backup-$(date +%Y%m%d)
mv data/evaluation.db.new data/evaluation.db

# 7. Restart ARGUS
./scripts/start_live.sh

# 8. After next successful session confirms health, delete the backup
# rm data/evaluation.db.backup-YYYYMMDD
\`\`\`

## Reclaim procedure 2: nuclear `rm` (when disk pressure precludes VACUUM INTO)

**Pre-condition:** `df -h /` does NOT have ≥ 2× DB size free.

**What you lose:**

- Historical Observatory drill-down for past dates (typically unused).
- Per-strategy decision-history queries for past dates via `/api/v1/strategies/{id}/evaluations?date=YYYY-MM-DD`.

**What you do NOT lose:**

- Today's Observatory (the in-memory ring buffer is independent until persisted).
- Past `logs/debrief_YYYY-MM-DD.json` files (separate artifacts).
- All trade history (`argus.db`).
- Counterfactual data (`counterfactual.db`).
- Learning Loop state (`learning.db`).
- Quality history.

\`\`\`bash
# 1. Stop ARGUS cleanly
./scripts/stop_live.sh

# 2. Verify down + no FD pins (CRITICAL — see chicken-and-egg trap below)
ps -axo pid,etime,command | grep -E "argus\.main|uvicorn argus" | grep -v grep
lsof data/evaluation.db 2>&1 | head

# 3. If FDs are pinned, kill the holders
# (typical culprit: zombie pytest workers — see DEF-235)
# kill -TERM <pids>; sleep 2; kill -KILL <surviving pids>

# 4. Delete
rm data/evaluation.db data/evaluation.db-wal data/evaluation.db-shm

# 5. Verify disk reclaimed
df -h /

# 6. Restart ARGUS — schema recreated from migrations on first init
./scripts/start_live.sh
\`\`\`

## Chicken-and-egg disk-pressure trap

If `data/evaluation.db` has grown so large that the disk is full, you cannot VACUUM INTO (needs ~2× source size on the same volume) and you may not be able to clean external caches enough to free that much space. `rm` is the fallback. Pre-VACUUM headroom check (Sprint 31.915 / G4) prevents the silent ENOSPC version of this; documented here for operator awareness.

## Sibling-process FD-pinning trap (Apr 28 incident)

When `rm`-ing a SQLite DB that other processes have open (even pytest workers from earlier in the day), the inode is unlinked but the blocks are not released. `df -h` will show only marginal recovery. `lsof <path>` reveals the holders. Kill the holders to release the bytes.

This was observed during the Apr 28 incident: 25.6 GB DB, `rm` recovered only 1 GB initially because 3 zombie pytest workers (`tests/test_main.py::TestOrchestratorIntegration::test_orchestrator_in_app_state`) had FDs open. After killing the workers, recovery completed. See DEF-235.

## When to call this an architectural problem

If `evaluation.db` ever grows beyond the steady-state target by more than 50% (i.e., > 15 GB at the current `RETENTION_DAYS=2` policy), reopen the investigation. The retention task is firing-but-not-deleting (file a sibling DEF), or the write-volume has changed (file a sibling DEF and consider a daily-rollup architecture).
```

### C4. Update CLAUDE.md

Add the 5 new DEF rows (DEF-231 through DEF-235) to the DEF table per `.claude/rules/doc-updates.md` numbering hygiene:

```markdown
| ~~DEF-231~~ | ~~`evaluation.db` retention deletion fires silently~~ | — | **RESOLVED-IN-SPRINT** (Sprint 31.915 Session 1, anchor `<TBD>`). Root cause: <Phase A finding>. Fix: <2-line change>. Regression test: `tests/test_telemetry_store.py::test_retention_logs_success_path`. |
| ~~DEF-232~~ | ~~`evaluation.db` pre-VACUUM disk-headroom check missing~~ | — | **RESOLVED-IN-SPRINT** (Sprint 31.915 Session 1). `_vacuum()` now refuses to run when `shutil.disk_usage(volume).free < headroom_multiplier × current_db_size`. Logs WARNING + aborts cycle. Regression tests: `tests/test_telemetry_store.py::test_pre_vacuum_disk_headroom_check_*`. |
| ~~DEF-233~~ | ~~`evaluation.db` operational visibility absent from `/health`~~ | — | **RESOLVED-IN-SPRINT** (Sprint 31.915 Session 1). `/health` JSON now includes `evaluation_db.{size_mb, last_retention_run_at_et, last_retention_deleted_count, freelist_pct}`. Regression test: `tests/api/test_health.py::test_health_endpoint_exposes_evaluation_db_subfields`. |
| ~~DEF-234~~ | ~~Hardcoded `RETENTION_DAYS = 7` incompatible with operator's disk environment~~ | — | **RESOLVED-IN-SPRINT** (Sprint 31.915 Session 1). `EvaluationStoreConfig` Pydantic model in `argus/core/config.py`; `config/evaluation_store.yaml` standalone overlay (DEC-384 pattern); default `RETENTION_DAYS = 2` (DEC-389). Regression test: `tests/test_telemetry_store.py::test_retention_days_is_config_driven`. |
| DEF-235 | `tests/test_main.py::TestOrchestratorIntegration::test_orchestrator_in_app_state` hangs indefinitely under single-test invocation, pinning FDs of deleted files | Sprint 31.915 / Apr 28 disk-pressure incident | **Status:** OPEN — DEFERRED — Routing: opportunistic in next `tests/test_main.py` hygiene pass. Sibling-class to DEF-049 (`test_orchestrator_uses_strategies_from_registry` single-test fallthrough). Symptom observed Apr 28: 3 zombie workers from `~14h-old pytest invocations held FDs on `data/evaluation.db` after operator `rm`; `df -h` showed only marginal recovery until zombies killed. Likely root cause: same `data_dir: "data"` relative-path mechanism documented in DEF-049's resolution comment at `tests/test_main.py:883-888`. Fix candidate: tighten `data_dir` to absolute, OR add a hard `pytest-timeout` to the test class. |
```

Also update CLAUDE.md's "Current State" Tests line:
- Pytest count: 5,269 → 5,275 (+6 minimum from this session).
- Add the line `Sprint 31.915 sealed 2026-04-29` to recent-sprints area.

### C5. Update `docs/decision-log.md` and `docs/dec-index.md`

`decision-log.md`: append DEC-389 entry. Mirror the structural format of DEC-385/386/388 — title line + 1–2 paragraphs of architectural narrative + cross-refs to DEF-234 + IMPROMPTU-10's DEF-197 closure.

`dec-index.md`: append `- ● **DEC-389**: Config-Driven `evaluation.db` Retention — `EvaluationStoreConfig` Pydantic model + `config/evaluation_store.yaml` standalone overlay; default `RETENTION_DAYS = 2` (was 7). Supersedes implicit policy from DEF-197 closure (Sprint 31.9 IMPROMPTU-10).`

Update the index header line: `> 388 decisions (DEC-001 through DEC-389; DEC-387 freed during Sprint 31.91 planning)`.

### C6. Mid-sprint doc-sync manifest

Per `protocols/mid-sprint-doc-sync.md`. Write `docs/sprints/sprint-31.915-evaluation-db-retention/doc-sync-manifest.md`:

```markdown
# Sprint 31.915 Doc-Sync Manifest

## Triggering event
Sprint 31.915 Session 1 close-out files 5 new DEFs (DEF-231 through DEF-235) and 1 new DEC (DEC-389), changing CLAUDE.md DEF-table state and decision-log state mid-flight.

## Files touched

| File | Change shape | Sprint-close transition owed |
|---|---|---|
| CLAUDE.md | DEF table: append 5 rows (DEF-231/232/233/234 strikethrough RESOLVED-IN-SPRINT, DEF-235 OPEN-DEFERRED); Current State pytest count update | DEF-231/232/233/234 strikethrough verified at sprint close; DEF-235 routing confirmed |
| docs/decision-log.md | Append DEC-389 entry | DEC-389 present and well-formed |
| docs/dec-index.md | Append DEC-389 line; update header count | Header count = 389 |
| docs/sprint-history.md | Append Sprint 31.915 row | Row present with anchor commit |
```

### C7. Closeout

Per `.claude/skills/close-out.md`. Write `docs/sprints/sprint-31.915-evaluation-db-retention/session-1-closeout.md`. Include:

1. Phase A diagnostic findings reference (`dev-logs/2026-04-28_retention-mechanism-diagnostic.md`).
2. Phase B implementation summary, anchor commit SHA.
3. Phase C tests/runbook/closeout summary.
4. Required `---BEGIN-CLOSE-OUT---` block per template.
5. Required `json:structured-closeout` JSON appendix per template.
6. Self-Assessment: CLEAN unless Phase A surprises occurred.
7. Green CI URL.

## Constraints

- Do NOT modify: `argus/data/migrations/evaluation.py` or any other file under `argus/data/migrations/` (Sprint 31.91 Impromptu C territory).
- Do NOT modify: `argus/intelligence/counterfactual_store.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/learning/learning_store.py`, `argus/data/vix_data_service.py`, `argus/intelligence/storage.py`, `argus/core/regime_history.py`, `argus/api/routes/alerts.py` (sibling SQLite stores; out of scope).
- Do NOT modify the existing 3 IMPROMPTU-10 lifecycle tests in `tests/test_telemetry_store.py` except for the one-line `RETENTION_INTERVAL_SECONDS` monkeypatch surgical adaptation in Phase B.3a (called out in Judgment Calls).
- Do NOT modify the 5 Sprint 31.8 VACUUM tests in `tests/strategies/test_telemetry_store_vacuum.py` (regression-only).
- Do NOT add a `--skip-headroom-check` flag, an env var override, or any other bypass for G4's pre-VACUUM check (RULE-039 non-bypassable validation).
- Do NOT use `getattr(obj, "field", default)` patterns in any new code (RULE-042 silent-default anti-pattern).
- Do NOT cross-reference other session prompts. This prompt is standalone.
- Do NOT modify `workflow/` submodule (RULE-018).
- Do NOT force-push to `main`. HITL-on-`main`.
- Do NOT restart ARGUS at session end — that's an operator action AFTER review CLEAR.
- Do NOT write a DEC-389 narrative that contradicts the IMPROMPTU-10 closeout's framing (DEC-389 supersedes the implicit policy, but does not invalidate IMPROMPTU-10's mechanism — IMPROMPTU-10's periodic-task pattern remains correct; only the cadence and threshold change).

## Test Targets

After implementation:
- Existing tests: all 5,269 must still pass.
- New tests: 6 minimum (5 in `tests/test_telemetry_store.py`, 1 in `tests/api/test_health.py`); +1 if Phase A produces a non-H1 root cause.
- Final command (full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`. Must show ≥5,275 tests, all passing.

## Visual Review

N/A — backend-only session; no UI touchpoints.

## Definition of Done

- [ ] Phase A diagnostic complete; findings written to `dev-logs/2026-04-28_retention-mechanism-diagnostic.md`.
- [ ] `scripts/diag_retention_logging.py` deleted post-Phase-A (single-use).
- [ ] G2 — `EvaluationStoreConfig` Pydantic model created and registered in standalone-overlay registry.
- [ ] `config/evaluation_store.yaml` created with documented defaults.
- [ ] G3 — both retention branches log INFO; existing IMPROMPTU-10 success-path log line retained verbatim where possible.
- [ ] G1 fix applied per Phase A finding (most likely: rowcount-before-commit).
- [ ] G4 — pre-VACUUM disk-headroom check active; both branches tested.
- [ ] G5 — `/health` endpoint exposes `evaluation_db` subfields; backend test passes.
- [ ] G6 — `docs/operations/evaluation-db-runbook.md` written (2 pages).
- [ ] G7 — ≥6 new pytest, all passing.
- [ ] CLAUDE.md DEF table: DEF-231/232/233/234 strikethrough RESOLVED-IN-SPRINT; DEF-235 OPEN-DEFERRED.
- [ ] `docs/decision-log.md`: DEC-389 entry appended.
- [ ] `docs/dec-index.md`: DEC-389 line appended; header count updated.
- [ ] `docs/sprint-history.md`: Sprint 31.915 row appended.
- [ ] Mid-sprint doc-sync manifest written.
- [ ] Close-out written to file.
- [ ] Tier 2 review CLEAR or CONCERNS_RESOLVED.
- [ ] Green CI URL cited in close-out.

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|---|---|
| Migration call site untouched | `git diff main -- argus/strategies/telemetry_store.py` shows no change to the line containing `apply_migrations` |
| IMPROMPTU-10 tests preserved | `git log -p main -- tests/test_telemetry_store.py` shows only ADDITIONS at file end + the one-line monkeypatch adaptation |
| Sprint 31.8 VACUUM tests untouched | `git diff main -- tests/strategies/test_telemetry_store_vacuum.py` is empty |
| Sibling stores untouched | `git diff --name-only main` does not include any of `argus/intelligence/counterfactual_store.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/learning/learning_store.py`, `argus/data/vix_data_service.py`, `argus/intelligence/storage.py`, `argus/core/regime_history.py`, `argus/api/routes/alerts.py` |
| Migration framework untouched | `git diff --name-only main` does not include any file under `argus/data/migrations/` |
| Workflow submodule untouched | `git diff --name-only main -- workflow/` is empty |
| Pre-VACUUM check is non-bypassable | `grep -nE "skip.headroom\|bypass.headroom\|--skip-headroom" argus/strategies/telemetry_store.py` returns empty |
| Pytest baseline preserved | `python -m pytest --ignore=tests/test_main.py -n auto -q` → ≥5,275 tests, all passing |
| Vitest baseline preserved | Frontend tests not touched; Vitest count unchanged at 913 |
| DEC-389 well-formed | `grep -A 5 "DEC-389" docs/decision-log.md` shows full entry; cross-refs to DEF-234 and DEF-197 |
| Health endpoint subfield contract | `curl -s http://localhost:8000/health \| jq .evaluation_db` returns all 4 keys (manual verification at restart, NOT automated in this session) |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include the structured JSON appendix at the end, fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330): `docs/sprints/sprint-31.915-evaluation-db-retention/session-1-closeout.md`.

Do NOT just print the report in the terminal. Create the file, write the full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the `@reviewer` subagent to perform the Tier 2 review within this same session.

Provide the `@reviewer` with:
1. The review context: `docs/sprints/sprint-31.915-evaluation-db-retention/sprint-spec.md` (this sprint's spec).
2. The close-out report path: `docs/sprints/sprint-31.915-evaluation-db-retention/session-1-closeout.md`.
3. The diff range: `git diff <pre-session-SHA>..HEAD` (use the SHA you recorded at session start).
4. The test command: `python -m pytest --ignore=tests/test_main.py -n auto -q` (full suite — this is the final session of the sprint).
5. Files that should NOT have been modified:
   - `argus/data/migrations/` (any file)
   - `argus/intelligence/counterfactual_store.py`
   - `argus/intelligence/experiments/store.py`
   - `argus/intelligence/learning/learning_store.py`
   - `argus/data/vix_data_service.py`
   - `argus/intelligence/storage.py`
   - `argus/core/regime_history.py`
   - `argus/api/routes/alerts.py`
   - `tests/strategies/test_telemetry_store_vacuum.py`
   - `workflow/` (submodule)
   - any frontend file

The `@reviewer` will produce its review report (including a structured JSON verdict fenced with ` ```json:structured-verdict `) and write it to: `docs/sprints/sprint-31.915-evaluation-db-retention/session-1-review.md`.

## Post-Review Fix Documentation

If the `@reviewer` reports CONCERNS and you fix the findings within this same session, you MUST update both the close-out and the review files per the standard implementation-prompt template (append "Post-Review Fixes" section to close-out, append "Post-Review Resolution" annotation to review, change verdict JSON from `"verdict": "CONCERNS"` to `"verdict": "CONCERNS_RESOLVED"`).

## Session-Specific Review Focus (for @reviewer)

1. **Phase A evidence is concrete.** The diagnostic findings in `dev-logs/2026-04-28_retention-mechanism-diagnostic.md` must contain raw rowcount values (before/after commit), not summaries. A "we believe H1" conclusion without rowcount evidence is inadmissible.
2. **Fix shape matches Phase A finding.** If Phase A confirmed H1 (rowcount-after-commit), the fix must capture rowcount BEFORE `await self._conn.commit()`. If H2/H3, the fix must address the corresponding mechanism.
3. **Regression test actually regresses.** Mentally revert the G1 fix (move `deleted = cursor.rowcount` back to after `commit`) and confirm `test_retention_logs_success_path` would fail.
4. **G4 is non-bypassable.** No `--skip-headroom-check` flag, no env var, no `try / except / pass` around the headroom calculation. RULE-039.
5. **G5 surfaces 4 fields.** Not 3, not 5. Exact contract: `size_mb`, `last_retention_run_at_et`, `last_retention_deleted_count`, `freelist_pct`.
6. **DEC-389 supersedes politely.** The DEC entry must reference DEF-197 (IMPROMPTU-10's closure) without invalidating IMPROMPTU-10's mechanism. The 4-hour periodic-task pattern is preserved; only the cadence+threshold defaults change.
7. **Migration call site is byte-for-byte unchanged.** `apply_migrations(self._conn, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)` at `argus/strategies/telemetry_store.py:84` is structurally inviolable.
8. **No silent-default anti-patterns.** No `getattr(config, "retention_days", 7)` (RULE-042). Either `config.retention_days` (Pydantic guarantees presence) or explicit `if config is None: config = EvaluationStoreConfig()`.

## Sprint-Level Regression Checklist (for @reviewer)

| Check | How to Verify |
|---|---|
| Migration framework path unaffected | `git diff <SHA>..HEAD -- argus/data/migrations/` is empty |
| IMPROMPTU-10 lifecycle tests structurally preserved | `git log -p <SHA>..HEAD -- tests/test_telemetry_store.py` shows only ADDITIONS + 1-line monkeypatch surgical adaptation |
| Sprint 31.8 VACUUM tests unmodified | `git diff <SHA>..HEAD -- tests/strategies/test_telemetry_store_vacuum.py` is empty |
| No sibling SQLite store touched | grep above |
| `workflow/` submodule untouched | `git diff <SHA>..HEAD -- workflow/` is empty |
| Full pytest green | full suite command exits 0; ≥5,275 tests pass |
| Vitest green | `cd argus/ui && npm test -- --run` exits 0 |
| Net pytest delta ≥ +6 | structured close-out JSON `tests.new` ≥ 6 |
| CLAUDE.md DEF table self-consistent | DEF-231/232/233/234 strikethrough; DEF-235 OPEN |
| DEC-389 well-formed | indexed in dec-index.md and full entry in decision-log.md |
| Sprint folder structure complete | All 5 expected files present |

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:

- Phase A diagnostic produces no conclusive root cause; G1 fix shipped on speculation.
- `argus/data/migrations/evaluation.py` modified in any way.
- IMPROMPTU-10 lifecycle tests modified beyond the 1-line monkeypatch surgical adaptation.
- `RETENTION_DAYS` default in code differs from what the YAML config sets.
- VACUUM pre-headroom check has a bypass flag.
- Health subfield writes to a different DB or namespace than `data/evaluation.db`.
- More than 8 files modified outside the explicit allow-list (scope creep; explicit allow-list: `argus/strategies/telemetry_store.py`, `argus/core/config.py`, `argus/core/health.py`, `argus/main.py`, `argus/api/server.py`, `config/evaluation_store.yaml`, `tests/test_telemetry_store.py`, `tests/api/test_health.py`, `docs/operations/evaluation-db-runbook.md`, `CLAUDE.md`, `docs/decision-log.md`, `docs/dec-index.md`, `docs/sprint-history.md`, `docs/sprints/sprint-31.915-evaluation-db-retention/*`, `dev-logs/2026-04-28_retention-mechanism-diagnostic.md`).
- Pytest or Vitest count regresses.
- DEC-389 written but DEF-234 not strikethrough.
- ARGUS restarted at session end (that's an operator action; reviewer should NOT trigger restart either).
