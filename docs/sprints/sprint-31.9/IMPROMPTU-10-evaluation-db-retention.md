# Sprint 31.9 IMPROMPTU-10: `evaluation.db` Retention Diagnostic + Fix

> Drafted Phase 2 post-Apr-23-debrief. Paste into a fresh Claude Code session.
> This prompt is **standalone** — do not read other session prompts in this campaign.

## Scope

**Finding addressed:** DEF-197 — `data/evaluation.db` is accumulating ~4.5 GB per session. April 22 boot: 4,776.3 MB. April 23 boot: 9,294.2 MB (+94.6%). Freelist 0.0% on both — rules out "VACUUM failing to reclaim." Most likely cause: retention `DELETE` is firing but not deleting any rows (wrong date comparison, wrong timezone, or trading_date column drift), OR retention is scheduled-at-startup-only and that single DELETE is losing the race against the ingestion rate. Linear extrapolation: 30 GB in a week, 150 GB in a month. Waiting for scheduled post-31.9-component-ownership slot means 25–50 GB at that time — boot init would exceed DEF-164's grace window and collide with auto-shutdown.

**Priority:** elevated MEDIUM → HIGH by April 23 debrief trajectory. Pulled forward from "opportunistic / next data-layer touch" into dedicated Sprint 31.9 session.

**Files touched:**
- `argus/strategies/telemetry_store.py` (primary — `EvaluationEventStore` retention + scheduler)
- `argus/main.py` (possibly — scheduler wiring or periodic task registration)
- `tests/strategies/test_telemetry_store.py` (regression test — retention fires, deletes, VACUUMs)
- `CLAUDE.md` (DEF-197 strikethrough + commit SHA)
- `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` (DEF-197 moved to Resolved)
- `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` (Stage 9B IMPROMPTU-10 row)

**Safety tag:** `safe-during-trading`. `evaluation.db` writes are fire-and-forget via strategy eval_buffer → SQLite; the retention fix wires in scheduling and a single-DELETE / VACUUM cycle without touching the write path.

**Theme:** Diagnose, fix, regression-test. Keep scope tight — do not refactor the fire-and-forget write pattern, do not move to a different DB engine, do not cluster with DEF-192 aiosqlite ResourceWarning category-(i) work (separate concern).

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
# Paper trading MAY continue.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count: __________ (expected: 5077 post-IMPROMPTU-08)
```

### 3. Branch & workspace

```bash
git checkout main && git pull --ff-only
git status  # Expected: clean
```

## Diagnostic Phase (required first — before any code changes)

Run these read-only queries against the actual `data/evaluation.db` and paste results into the close-out's "Diagnostic Findings" section:

```bash
# Q1: Row count + date span
sqlite3 data/evaluation.db <<'EOF'
SELECT MIN(trading_date), MAX(trading_date), COUNT(*),
       COUNT(DISTINCT trading_date) AS distinct_days
FROM evaluation_events;
EOF

# Q2: Rows per day — are there rows >7 days old still present?
sqlite3 data/evaluation.db <<'EOF'
SELECT trading_date, COUNT(*) AS rows
FROM evaluation_events
GROUP BY trading_date
ORDER BY trading_date DESC
LIMIT 30;
EOF

# Q3: DB file size + freelist
sqlite3 data/evaluation.db <<'EOF'
PRAGMA page_count;
PRAGMA page_size;
PRAGMA freelist_count;
EOF
ls -l data/evaluation.db | awk '{print $5 " bytes"}'
```

**Hypothesis tree:**
- If Q1 spans >7 days → retention DELETE isn't firing or isn't matching rows. Investigate `cleanup_old_events()` invocation path.
- If Q1 spans ≤7 days but Q3 shows high page_count → rows are within retention but ingestion rate exceeds retention window; the single-cleanup-at-startup pattern can't keep up. Need periodic retention scheduler.
- If freelist >0 → VACUUM isn't reclaiming. Investigate `_vacuum()`.

Record the hypothesis that matches your findings.

## Requirements

### R1: Identify and fix the retention wiring gap

Current state (verified from grep):
- `EvaluationEventStore.cleanup_old_events()` exists at `argus/strategies/telemetry_store.py:262`
- Called exactly twice in repo: `argus/main.py:919` (Phase 10.3 startup) and `argus/api/server.py:331` (lifespan init — alternate path)
- **No periodic scheduler.** If retention depends on the startup DELETE catching up with each session's ingestion, and the ingestion pace grew (current data: +4.5 GB/day, ~900K eval events/session), the single startup DELETE may not be closing the gap.

**Fix candidates (pick the one your diagnostic supports):**

1. **Periodic retention task** — add an `asyncio.create_task(self._run_periodic_retention())` in `EvaluationEventStore.initialize()` (or as a `main.py` post-Phase-10.3 registration). Cadence: every 4 hours. Gated by `_shutdown` flag (cancel on shutdown).
2. **Date-cutoff correction** — if Q1 shows dates like `2026-04-23` stored as `trading_date` but the cutoff SQL compares against `(datetime.now(_ET) - timedelta(days=7)).strftime("%Y-%m-%d")`, and timezone mismatch means the cutoff is off-by-one or stuck — fix the cutoff.
3. **Timezone/column fix** — if `trading_date` column stores UTC dates but cutoff uses ET, dates near midnight-ET can be persistently-older-than-cutoff even for current data.

Most likely: (1) — periodic scheduler is missing. Verify by running the diagnostic, then picking.

### R2: Regression test

Add to `tests/strategies/test_telemetry_store.py`:

- `test_cleanup_old_events_deletes_rows_older_than_retention_days` — insert rows at `trading_date = date.today() - timedelta(days=10)`, call `cleanup_old_events()`, assert rows deleted + freelist non-zero pre-vacuum.
- `test_cleanup_old_events_vacuums_after_delete` — insert + delete + assert file size decreases.
- If adding periodic scheduler: `test_periodic_retention_task_registers_and_cancels_cleanly` — start, verify task is scheduled, trigger shutdown, assert cancelled (no `CancelledError` leak).

Test target: +2 to +3 new pytest.

### R3: Optional one-shot cleanup script (DOCUMENTED in close-out, NOT committed code)

Document in the close-out a one-time operator step to reclaim the ~9 GB pre-fix accumulation:

```bash
# One-shot: copy last 7 days to fresh DB, swap in place
sqlite3 data/evaluation.db <<'EOF'
VACUUM INTO 'data/evaluation.db.new';
EOF
# Verify row counts match
sqlite3 data/evaluation.db.new "SELECT COUNT(*) FROM evaluation_events;"
sqlite3 data/evaluation.db "SELECT COUNT(*) FROM evaluation_events WHERE trading_date >= date('now', '-7 days');"
# If counts match, swap
mv data/evaluation.db data/evaluation.db.backup-YYYYMMDD
mv data/evaluation.db.new data/evaluation.db
# Delete backup after next successful boot confirms OK
```

This step is run manually by the operator AFTER the retention fix lands and one paper session has verified the scheduler fires without regression. Not a committed script.

### R4: CLAUDE.md strikethrough

Mark DEF-197 as RESOLVED with commit SHA + IMPROMPTU-10 pointer.

### R5: DEF-192 aiosqlite concern

If the fix opens a new `sqlite3.Connection` for VACUUM (the current pattern does this via `_vacuum()` → `asyncio.to_thread`), ensure the new connection is explicitly closed. Check against DEF-192 category (i) to verify no new `ResourceWarning` is introduced by this session. Target: aiosqlite resource warning count unchanged or reduced.

## Definition of Done

- [ ] Diagnostic Q1/Q2/Q3 output pasted into close-out
- [ ] Hypothesis identified + fix implemented
- [ ] 2–3 new regression pytest tests (target)
- [ ] `cleanup_old_events()` invocation audit documented — before + after
- [ ] `CLAUDE.md` DEF-197 strikethrough with commit SHA + RESOLVED annotation
- [ ] `RUNNING-REGISTER.md` DEF-197 moved to "Resolved this campaign"
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` Stage 9B IMPROMPTU-10 row marked CLEAR
- [ ] Close-out at `docs/sprints/sprint-31.9/IMPROMPTU-10-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/IMPROMPTU-10-review.md`
- [ ] One-shot operator cleanup step documented in close-out (not committed code)
- [ ] Green CI URL cited

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Diagnostic queries produce concrete evidence | Close-out §Diagnostic Findings has Q1/Q2/Q3 output |
| Retention DELETE actually fires on next startup | New pytest invokes + asserts row deletion |
| VACUUM executes after DELETE | New pytest asserts file-size decrease |
| If periodic task: scheduler registers + cancels cleanly | New pytest or shutdown path check |
| No DEF-192 category-(i) regression | Warning count from test run unchanged or reduced |
| Full suite net delta ≥ +2 | pytest count comparison |
| No unrelated files modified | `git diff --name-only` ≤6 files |

## Constraints

- DO NOT refactor the fire-and-forget write pattern
- DO NOT change `EvaluationEventStore.RETENTION_DAYS` default
- DO NOT touch DEF-192 aiosqlite warning category-(i) infrastructure — separate scope
- DO NOT run the one-shot cleanup (`VACUUM INTO`) as part of this session — document as operator step
- DO NOT modify the `workflow/` submodule (RULE-018)
- Work on `main`

## Test Targets

- `+2 to +3` new pytest (scope-matching)
- `+0` Vitest (no UI impact)
- Full pytest suite stays green

## Close-Out

Write close-out to: `docs/sprints/sprint-31.9/IMPROMPTU-10-closeout.md`

Include:
1. **Diagnostic Findings** — Q1/Q2/Q3 raw output + hypothesis confirmed
2. **Fix chosen** — which candidate (1/2/3) was implemented + why
3. **Before/After size evidence** — `data/evaluation.db` size delta if one-shot cleanup run (operator step)
4. **Invocation audit** — where `cleanup_old_events()` now fires + cadence
5. **Test additions** — new pytest names + what they assert
6. **DEF-192 category-(i) warning count** — before/after
7. **Operator one-shot cleanup step** — documented, not committed
8. **Green CI URL**

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

Provide:
1. This kickoff
2. Close-out path
3. Diff range
4. Files that should NOT have been modified:
   - `workflow/` submodule
   - Any audit-2026-04-21 doc back-annotation
   - `argus/execution/order_manager.py`
   - `argus/api/auth.py`
   - `config/experiments.yaml`
   - `argus/intelligence/counterfactual_store.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/learning/learning_store.py` (other SQLite stores — separate concern)
   - Any frontend file
5. Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q`

## Session-Specific Review Focus (for @reviewer)

1. **Diagnostic evidence is concrete.** Q1/Q2/Q3 raw output must be in the close-out. A "retention isn't firing" conclusion without SQL output is inadmissible.
2. **Fix matches hypothesis.** If the diagnostic shows data >7 days old, the fix must address the DELETE not firing/matching. If the diagnostic shows all data ≤7 days but file still growing, the fix must address periodic rescheduling.
3. **Regression test actually regresses.** Revert the fix, confirm the test fails. Document the mental revert in the close-out.
4. **No DEF-192 regression.** Warning count before/after.
5. **Operator one-shot cleanup is documented, not committed.** No `VACUUM INTO` in the diff.
6. **Scope ≤6 files.** If more files are touched, question why.
7. **Green CI URL cited.**

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta ≥ +2
- Vitest count unchanged
- No scope boundary violation (see list above)
- CLAUDE.md DEF-197 strikethrough with commit SHA

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- `EvaluationEventStore.RETENTION_DAYS` value changed (should be 7, unchanged)
- Fire-and-forget write pattern refactored (out of scope)
- Other SQLite stores touched (counterfactual, experiments, learning — separate scope)
- One-shot `VACUUM INTO` committed as code (should be operator doc only)
- `workflow/` submodule modified
- DEF-192 warning count regressed
- Full pytest suite broken post-session
- Audit-report back-annotation modified

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **Hypothesis confirmed + fix chosen**
4. **One-shot cleanup step** (for operator to execute manually post-session)
5. **Expected next-session DB size** after one-shot cleanup + retention running
6. Green CI URL
7. One-line summary: `IMPROMPTU-10 complete. Close-out: {verdict}. Review: {verdict}. Diagnostic: {hypothesis}. Fix: {candidate}. Commits: {SHAs}. Test delta: {pre} → {post} pytest. CI: {URL}. DEF-197 closed.`
