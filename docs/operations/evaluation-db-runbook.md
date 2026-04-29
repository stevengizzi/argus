# Operator Runbook — `data/evaluation.db`

> Sprint 31.915 (DEC-389) — supersedes IMPROMPTU-10 §7 documentation.
> Last updated: 2026-04-28.

## What this DB is

`data/evaluation.db` is the persistent backing store for
`StrategyEvaluationBuffer` events — every `ENTRY_EVALUATION` /
`CONDITION_CHECK` / `SIGNAL_*` record produced by every strategy is fired
into the in-memory ring buffer (`StrategyEvaluationBuffer`, `maxlen=1000`)
AND fire-and-forget-written to this SQLite file. The schema is owned by
`argus/data/migrations/evaluation.py` (Sprint 31.91 Impromptu C). The
ObservatoryService and the strategy-decisions REST endpoints
(`/api/v1/strategies/{id}/decisions?date=YYYY-MM-DD`) read from it for
historical drill-down. Daily ingestion is roughly 5 GB.

Retention is config-driven via `EvaluationStoreConfig`
(`config/evaluation_store.yaml`, DEC-389). Default policy:
`retention_days = 2`, `retention_interval_seconds = 14400` (4 hours),
`size_warning_threshold_mb = 2000`, `pre_vacuum_headroom_multiplier = 2.0`.
The periodic retention task (`EvaluationEventStore._run_periodic_retention`)
fires `cleanup_old_events()` every 4 hours; a startup-reclaim VACUUM
fires once at boot when the freelist ratio exceeds 50% and the file
exceeds 500 MB.

## Symptoms → diagnosis quick table

| Symptom | First check | Likely cause |
|---|---|---|
| `df -h /` < 5 GB free | `du -sh data/evaluation.db` | DB > steady-state target |
| `EvaluationEventStore: DB size N MB exceeds threshold` WARNING at boot | Inspect `config/evaluation_store.yaml` `retention_days` | Operator-disk-environment mismatch |
| No `retention scanned (cutoff X, 0 rows matched)` INFO lines for >5 hours | `curl /api/v1/health \| jq .evaluation_db.last_retention_run_at_et` | Periodic retention task crashed silently (DEF-231 family) |
| `headroom check FAILED` WARNING | `df -h <volume>` and `lsof \| grep -i evaluation.db` | Chicken-and-egg disk pressure (G4 / DEF-232) |
| Disk recovers ~1 GB after `rm` of N GB file | `lsof \| grep -i evaluation.db` | Process holding deleted-inode FD; kill the process |
| `/health` `evaluation_db.last_retention_deleted_count` stays at 0 for days | Check `MAX(trading_date)` vs `today_et - retention_days` | Oldest data still inside retention window |
| `/health` `evaluation_db.size_mb` growing without bound | Check rate of writes vs retention cadence | Write volume exceeds steady-state model — file a sibling DEF |

## Diagnostic queries

```bash
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

# Q4 — observability via /health (no SQL required)
curl -sH "Authorization: Bearer $ARGUS_TOKEN" \
  http://127.0.0.1:8000/api/v1/health | jq .evaluation_db
```

## Reclaim procedure 1: `VACUUM INTO` (preferred when disk has headroom)

**Pre-condition:** `df -h /` shows free space ≥ 2× current
`data/evaluation.db` size. (Sprint 31.915 G4 enforces this gate at
runtime; this manual procedure mirrors the same constraint at the
operator level.)

```bash
# 1. Stop ARGUS cleanly
./scripts/stop_live.sh   # (or operator's preferred stop method)

# 2. Verify ARGUS is fully down
ps -axo pid,etime,command | grep -E "argus\.main|uvicorn argus" | grep -v grep
# Expected: empty.

# 3. Verify no FDs are pinning the file (Apr 28 incident — see DEF-235)
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
```

## Reclaim procedure 2: nuclear `rm` (when disk pressure precludes VACUUM INTO)

**Pre-condition:** `df -h /` does NOT have ≥ 2× DB size free.

**What you lose:**

- Historical Observatory drill-down for past dates (typically unused).
- Per-strategy decision-history queries for past dates via
  `/api/v1/strategies/{id}/decisions?date=YYYY-MM-DD`.

**What you do NOT lose:**

- Today's Observatory (the in-memory `StrategyEvaluationBuffer` ring
  buffer is independent until the next persisted write).
- Past `logs/debrief_YYYY-MM-DD.json` files (separate artifacts).
- All trade history (`argus.db`).
- Counterfactual data (`counterfactual.db`).
- Learning Loop state (`learning.db`).
- Quality history.

```bash
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
```

## Chicken-and-egg disk-pressure trap

If `data/evaluation.db` has grown so large that the disk is full, you
cannot `VACUUM INTO` (needs ~2× source size on the same volume) and you
may not be able to clean external caches enough to free that much space.
`rm` is the fallback. Sprint 31.915 G4's pre-VACUUM headroom check
(`pre_vacuum_headroom_multiplier=2.0`, non-bypassable per RULE-039)
prevents the silent-ENOSPC version of this case at runtime — the periodic
task aborts the VACUUM cycle with a loud WARNING rather than letting the
ENOSPC bubble through `_run_periodic_retention`'s broad-except. The
DELETE that just committed survives; only the VACUUM is skipped.

## Sibling-process FD-pinning trap (Apr 28 incident)

When `rm`-ing a SQLite DB that other processes have open (even pytest
workers from earlier in the day), the inode is unlinked but the blocks
are not released. `df -h` will show only marginal recovery.
`lsof <path>` reveals the holders. Kill the holders to release the
bytes.

This was observed during the Apr 28 incident: 25.6 GB DB, `rm` recovered
only 1 GB initially because 3 zombie pytest workers
(`tests/test_main.py::TestOrchestratorIntegration::test_orchestrator_in_app_state`)
had FDs open. After killing the workers, recovery completed. See
DEF-235 for the test-side root cause.

## Configuration tuning

The retention policy is tunable via `config/evaluation_store.yaml`. The
file uses bare-field shape (no top-level `evaluation_store:` wrapper) —
DEC-384 / FIX-02 standalone-overlay convention. The standalone-overlay
registry in `argus/core/config.py` deep-merges the YAML over
`SystemConfig.evaluation_store` at boot.

Field ranges (Pydantic-enforced):

| Field | Default | Range | What it does |
|---|---|---|---|
| `retention_days` | 2 | [1, 30] | ET trading days of `evaluation_events` to keep. Lowered from 7 (IMPROMPTU-10) per DEC-389. |
| `retention_interval_seconds` | 14400 | ≥60 | Periodic retention cadence in seconds. 4 hours default. |
| `startup_reclaim_min_size_mb` | 500 | ≥1 | Boot VACUUM fires only when DB exceeds this size (and freelist ratio gate also met). |
| `startup_reclaim_freelist_ratio` | 0.5 | [0.0, 1.0] | Boot VACUUM fires only when freelist exceeds this fraction of pages. |
| `size_warning_threshold_mb` | 2000 | ≥1 | Boot WARNING if DB exceeds this size after maintenance. |
| `pre_vacuum_headroom_multiplier` | 2.0 | [1.0, 10.0] | VACUUM aborts if `disk_free < N × current_db_size`. Non-bypassable per RULE-039. |

To tune in a session: edit `config/evaluation_store.yaml`, restart
ARGUS. Config-driven values apply at next `EvaluationEventStore.__init__`.

## When to call this an architectural problem

If `evaluation.db` ever grows beyond the steady-state target by more
than 50% (i.e., > 15 GB at the current `retention_days=2` policy),
reopen the investigation. Either:

- the retention task is firing-but-not-deleting (file a sibling DEF
  with `/health` `evaluation_db` snapshots over time),
- the write-volume has changed (file a sibling DEF and consider a
  daily-rollup architecture),
- or the periodic task has crashed silently (DEF-231 family — Sprint
  31.915's G3 always-log + G5 `/health` exposure should make this
  detectable within one retention cadence).
