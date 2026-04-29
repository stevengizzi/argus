# Sprint 31.915 — `evaluation.db` Retention Mechanism + Observability

> **Type:** Single-session impromptu (full-protocol).
> **Scope position:** Pulled forward ahead of Sprint 31.92 (component-ownership) per operator disposition 2026-04-28.
> **Origin:** post-Sprint-31.91 disk-pressure investigation (operator-led conversation, 2026-04-28). `data/evaluation.db` reached 25.6 GB, filled `/private/tmp` to ENOSPC, blocked Claude Code's Bash tool twice in a 24-hour window, and forced a manual nuke of the DB to relieve disk pressure.
> **Trigger:** IMPROMPTU-10 (Sprint 31.9, anchor `8bdec82`) was supposed to prevent unbounded growth via a periodic 4-hour retention task. The task is spawning, but Apr 24–28 logs show **zero `retention deleted N rows` INFO lines** despite the freelist transitioning from 0.0% → 0.9% between Apr 27 and Apr 28 boots — empirical evidence that retention IS firing but is invisibly silent.
> **Anchor commit:** TBD (set during session). Pre-session `main` HEAD: `210d2f9`.

---

## Why this is being run as a sprint, not a quick patch

The Apr 28 disk-pressure investigation surfaced three coupled concerns:

1. **The IMPROMPTU-10 fix has an unknown silent-failure mode.** Either retention is firing-but-not-logging-the-success-path (most likely: aiosqlite `cursor.rowcount` post-commit semantics), or VACUUM is failing silently after a successful DELETE. We do not know which. Without nailing the root cause, any new code we ship is a guess.

2. **`RETENTION_DAYS = 7` is incompatible with the operator's environment.** A 460 GB disk with ~5 GB/day of evaluation telemetry ingestion targets 30–35 GB steady-state under the current policy — about 7% of total disk. Combined with all other ARGUS storage (Parquet caches at 44.73 GB, 8 SQLite DBs, log files, snapshots), this leaves insufficient headroom under normal operation.

3. **The retention loop has zero operational visibility.** The current code only logs the success path when `deleted > 0`. The Apr 24 paper-session debrief explicitly flagged this as ambiguous evidence; the gap was carried forward into Apr 25–28 without resolution.

A single hot-patch addressing only (2) — lower `RETENTION_DAYS` — would ship with the same silent-failure mechanism intact. We need (1) diagnosed and (3) addressed in the same session, otherwise the next disk-pressure incident is a question of when, not if.

The investigation conversation with Claude.ai (operator: Steven, 2026-04-28 evening) covered Phase 1 read-only diagnostics through Phase 3 reclaim. Phase 4 (real fix) is what this sprint implements.

---

## Goals (single session, S1)

| # | Goal | Out-of-scope tells |
|---|---|---|
| G1 | Nail the root cause of why `cleanup_old_events()` does not log `retention deleted N rows` even when the DELETE clearly committed (freelist transitioned 0.0% → 0.9% Apr 27→28). | Touching code paths outside `argus/strategies/telemetry_store.py` for the diagnostic; speculating about the cause without instrumented evidence |
| G2 | Make `RETENTION_DAYS`, `RETENTION_INTERVAL_SECONDS`, `STARTUP_RECLAIM_FREELIST_RATIO`, `STARTUP_RECLAIM_MIN_SIZE_MB`, `SIZE_WARNING_THRESHOLD_MB` config-driven via Pydantic. New default: `RETENTION_DAYS = 2`. | Changing the migration-framework path (Impromptu C territory); changing the schema; refactoring the fire-and-forget write pattern |
| G3 | Always-log retention iterations regardless of `deleted` count. INFO when work was done, DEBUG-or-INFO when no rows matched. Eliminate the silent-on-zero-deletion gap. | Touching write-side log throttling (`_WARNING_INTERVAL_SECONDS` exists for a different concern) |
| G4 | Pre-VACUUM disk-headroom check that fails loud. Refuses to run VACUUM if free space on the volume is less than 2× current DB size. Loud WARNING + abort-this-cycle behavior. | Adding actual recovery logic (operator runbook covers manual reclaim); bypass flags |
| G5 | `/health` endpoint sub-fields surfacing `evaluation_db.size_mb`, `last_retention_run_at_et`, `last_retention_deleted_count`, `freelist_pct`. | Building a new endpoint; touching the 30-component health framework's structure |
| G6 | Operator runbook at `docs/operations/evaluation-db-runbook.md` documenting symptoms, diagnostic queries, the §7 `VACUUM INTO` procedure, and the chicken-and-egg disk-pressure trap. | Replicating the IMPROMPTU-10 closeout |
| G7 | Regression tests covering G2–G4. | Touching pre-existing IMPROMPTU-10 lifecycle tests in `tests/test_telemetry_store.py` (regress-by-modification risk) |

---

## DEF / DEC numbering plan

DEF high-water at session start: **DEF-230** (Sprint 31.91 D14 doc-sync, anchor `210d2f9`). DEC high-water: **DEC-388** (DEC-387 ⊗ FREED).

| ID | Title | Lifecycle |
|---|---|---|
| DEF-231 | `evaluation.db` retention deletion fires silently — no `retention deleted N rows` INFO line despite freelist evidence DELETE committed | OPEN at session start; RESOLVED-IN-SPRINT if G1 + G3 land |
| DEF-232 | `evaluation.db` pre-VACUUM disk-headroom check missing (chicken-and-egg ENOSPC class) | OPEN at session start; RESOLVED-IN-SPRINT by G4 |
| DEF-233 | `evaluation.db` operational visibility absent from `/health` endpoint | OPEN at session start; RESOLVED-IN-SPRINT by G5 |
| DEF-234 | Hardcoded `RETENTION_DAYS = 7` incompatible with operator's disk environment | OPEN at session start; RESOLVED-IN-SPRINT by G2 + DEC-389 |
| DEF-235 | `tests/test_main.py::TestOrchestratorIntegration::test_orchestrator_in_app_state` hangs indefinitely under single-test invocation, pinning FDs of deleted files | OPEN at session start; **deferred** (sibling-class to DEF-049; routing: opportunistic in next `tests/test_main.py` hygiene pass) |
| DEC-389 | `evaluation.db` retention is config-driven (`EvaluationStoreConfig` Pydantic model); `RETENTION_DAYS` default changed from 7 to 2 | NEW; supersedes implicit policy from DEF-197 closure |

DEFs DEF-231 / DEF-232 / DEF-233 / DEF-234 are filed as a batch in CLAUDE.md's DEF table at session start (before any implementation); they are resolved in-place via strikethrough at session close per `.claude/rules/doc-updates.md`. DEF-235 stays OPEN and deferred. DEC-389 is appended to `docs/decision-log.md` and indexed in `docs/dec-index.md`.

---

## Pre-flight state (anchored to operator-pasted Phase 1 diagnostic, 2026-04-28)

- `data/evaluation.db` and siblings (`-wal`, `-shm`) have been **deleted** by the operator. ARGUS is **down**. No FD pins remain (zombie pytest workers killed; `lsof` clean).
- `df -h /` shows ~19 Gi free. Margin is tight; G4's pre-VACUUM check is precisely sized for this environment.
- Migration framework (Sprint 31.91 Impromptu C, anchor `3fefda8`) owns the `evaluation` schema via `argus/data/migrations/evaluation.py`. Our changes must NOT break the migration call at `telemetry_store.py:84`.
- IMPROMPTU-10 lifecycle tests at `tests/test_telemetry_store.py` (anchored to commit `8bdec82`) must continue passing without modification — we will ADD new tests, never modify the existing 3.
- Sprint 31.91's `tests/strategies/test_telemetry_store_vacuum.py` (5 tests, anchored to commit `6ea45aa` from Sprint 31.8) must also pass unmodified.

---

## Approach (single session)

The session has three phases inside one Claude Code invocation. The phases are sequential — Phase A's findings shape Phase B's implementation choices. The boundaries are explicit in the impl prompt.

### Phase A — Instrumented Diagnostic (~30–60 min, READ-ONLY w.r.t. production code)

Goal: produce conclusive evidence of why `cleanup_old_events()`'s INFO log line did not fire on the Apr 27→28 retention iteration that demonstrably deleted Apr 20 rows.

Approach: a focused isolation script (NOT a pytest test) at `scripts/diag_retention_logging.py` that:

1. Creates a fixture `EvaluationEventStore` against a tempfile DB.
2. Inserts ~100 rows with `trading_date = (today_et - 10 days)` (clearly outside any retention window).
3. Calls `cleanup_old_events()` directly under the production logger configuration (NOT pytest's caplog).
4. Captures: aiosqlite `cursor.rowcount` value before and after `commit`, freelist transition, log lines emitted, exception traces if any.
5. Repeats with `trading_date = (today_et + 1 day)` (clearly INSIDE retention) to confirm the zero-deletion path.

Hypothesis tree (in priority order based on Phase 1 evidence):

| Hypothesis | What we'd observe | What we'd see in the script's output |
|---|---|---|
| H1: `cursor.rowcount` returns 0 on aiosqlite cursor post-`await commit()` | DELETE statement removes rows on disk; cursor.rowcount is 0; `if deleted > 0:` gate fails silently; VACUUM never runs | rowcount=0 in script output; row count delta in DB > 0 |
| H2: Logger config in production routes `argus.strategies.telemetry_store` INFO to a level that's not in any handler | DELETE works; rowcount > 0; `logger.info(...)` is called but written nowhere | rowcount>0 in script output; INFO line visible in script (because root handler level differs); but NO INFO line in production logs |
| H3: `_run_periodic_retention()` exception path fires but the WARNING is in a separate file or a separate logger | DELETE works; rowcount > 0; an exception is raised; WARNING fires under different logger name | exception trace visible |
| H4: Something else | Diagnostic must surface this loudly | structured findings document captures every step |

The script writes its findings to `dev-logs/2026-04-28_retention-mechanism-diagnostic.md` BEFORE Phase B begins. Phase B's implementation choices reference the findings.

### Phase B — Implementation (~2–3 hours)

Six file-touch targets, in dependency order:

1. **`config/evaluation_store.yaml`** (NEW) — the operator-facing config surface.
2. **`argus/core/config.py`** — new `EvaluationStoreConfig` Pydantic model added to the existing config tree; standalone overlay registry per DEC-384 (FIX-01).
3. **`argus/strategies/telemetry_store.py`** — class constants migrated to instance fields populated from config; G1's root-cause fix (specifics determined by Phase A); G3's always-log; G4's pre-VACUUM disk-headroom check; G5's last-run/last-deleted-count instance fields.
4. **`argus/core/health.py`** — new `evaluation_db` health subfield with size/last-run/last-deleted/freelist.
5. **`argus/main.py`** — pass config into `EvaluationEventStore.__init__`; pass store reference into `HealthMonitor` for the new subfield (or have store register itself with HealthMonitor).
6. **`argus/api/server.py`** — same config wiring for the alternate init path.

### Phase C — Tests + Runbook + Closeout (~1 hour)

1. New tests in `tests/test_telemetry_store.py` (existing file, append-only):
   - `test_retention_days_is_config_driven` — assert config-loaded value reaches the store.
   - `test_retention_logs_zero_deletion_path` — assert INFO line fires when `deleted == 0`.
   - `test_retention_logs_success_path` — assert INFO line fires when `deleted > 0` (regression guard against G1's silent-failure mode).
   - `test_pre_vacuum_disk_headroom_check_aborts_when_insufficient` — mock `shutil.disk_usage` to return < 2× DB size; assert VACUUM is NOT called and a WARNING fires.
   - `test_pre_vacuum_disk_headroom_check_proceeds_when_sufficient` — happy path; VACUUM runs.
   - Phase-A-specific regression test capturing the silent-failure mechanism (exact shape determined by Phase A findings).

2. New tests in `tests/api/test_health.py` (existing file, append-only):
   - `test_health_endpoint_exposes_evaluation_db_subfields` — assert all 4 fields present and correctly typed.

3. Runbook at `docs/operations/evaluation-db-runbook.md`:
   - Symptoms-to-diagnosis table (file > N GB → check freelist; freelist 0% → check retention logs; retention logs absent → run diagnostic script; etc.).
   - Diagnostic queries (the IMPROMPTU-10 Q1/Q2/Q3 SQL).
   - Two reclaim procedures:
     - **§7 procedure** — `VACUUM INTO` against a stopped ARGUS, with explicit pre-condition that free disk space ≥ 2× current DB size.
     - **Nuclear procedure** — `rm` against a stopped ARGUS, used when disk pressure precludes §7. Documents what's lost (historical Observatory drill-down for past dates) and what's not (live trading state, Counterfactual data, trade history, Learning Loop state, debrief JSONs already written).
   - Chicken-and-egg edge case explicitly named, with sequence: relieve disk → release any pinned FDs (`lsof | grep evaluation.db`; kill zombies) → VACUUM INTO or `rm`.
   - Sibling-process FD-pinning trap (lifted from the Apr 28 incident).
   - Cross-references DEF-235 for the test-zombie hang.

4. Closeout at `docs/sprints/sprint-31.915-evaluation-db-retention/session-1-closeout.md` per `.claude/skills/close-out.md`.

5. Mid-sprint doc-sync manifest at `docs/sprints/sprint-31.915-evaluation-db-retention/doc-sync-manifest.md` per `protocols/mid-sprint-doc-sync.md` — required because we file 5 new DEFs and 1 DEC.

6. Tier 2 review via `@reviewer` subagent within the same Claude Code session. CLEAR or CONCERNS_RESOLVED required.

---

## Constraints & non-goals

- **Do NOT** modify `argus/data/migrations/evaluation.py` or any migration framework code — Impromptu C owns that.
- **Do NOT** modify the existing 3 IMPROMPTU-10 lifecycle tests in `tests/test_telemetry_store.py` — only append.
- **Do NOT** modify the 5 Sprint 31.8 VACUUM tests in `tests/strategies/test_telemetry_store_vacuum.py` — only run them as regression check.
- **Do NOT** change the 30-component health framework's structure — only add an `evaluation_db` subfield using the existing `update_component()` or equivalent pattern.
- **Do NOT** refactor the fire-and-forget write pattern — out of scope per IMPROMPTU-10's original constraint.
- **Do NOT** touch `argus/intelligence/counterfactual_store.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/learning/learning_store.py`, `argus/data/vix_data_service.py`, `argus/intelligence/storage.py` (catalyst), `argus/core/regime_history.py`, `argus/api/routes/alerts.py` (operations.db owner) — sibling SQLite stores are out of scope.
- **Do NOT** modify `workflow/` submodule (RULE-018).
- **Do NOT** touch the migration call site `telemetry_store.py:84` — only fields ABOVE/BELOW it.
- **Do NOT** force-push to `main`. HITL-on-`main`.
- **Do NOT** restart ARGUS at session end — that's an operator action AFTER review CLEAR.

---

## Definition of Done

- [ ] DEF-231 root cause documented in `dev-logs/2026-04-28_retention-mechanism-diagnostic.md` with raw evidence.
- [ ] G2 — `EvaluationStoreConfig` Pydantic model loads from `config/evaluation_store.yaml`; default `RETENTION_DAYS = 2`.
- [ ] G3 — `cleanup_old_events()` logs both branches (zero-deletion and positive-deletion); regression test covers both.
- [ ] G4 — pre-VACUUM disk-headroom check active; aborts cycle when `shutil.disk_usage(volume).free < 2 × current_db_size_bytes`; logs WARNING; tests cover both branches.
- [ ] G5 — `/health` endpoint exposes `evaluation_db.{size_mb, last_retention_run_at_et, last_retention_deleted_count, freelist_pct}` subfields.
- [ ] G6 — runbook at `docs/operations/evaluation-db-runbook.md`, 2 pages, documents §7 + nuclear + chicken-and-egg + zombie-FD pattern.
- [ ] G7 — minimum +6 new pytest, all passing.
- [ ] CLAUDE.md DEF table updated: DEF-231/232/233/234 strikethrough RESOLVED-IN-SPRINT; DEF-235 OPEN-DEFERRED.
- [ ] DEC-389 entered in `docs/decision-log.md` and `docs/dec-index.md`.
- [ ] Mid-sprint doc-sync manifest written.
- [ ] Closeout written + Tier 2 review CLEAR/CONCERNS_RESOLVED.
- [ ] Green CI URL cited in closeout.
- [ ] Sprint folder structure: `docs/sprints/sprint-31.915-evaluation-db-retention/{sprint-spec.md, session-1-prompt.md, session-1-closeout.md, session-1-review.md, doc-sync-manifest.md}`.

---

## Sprint-level regression checklist

| Check | How to verify |
|---|---|
| Migration framework path unaffected | `grep -n "apply_migrations" argus/strategies/telemetry_store.py` returns the same line untouched (only fields above/below modified) |
| IMPROMPTU-10 lifecycle tests unmodified | `git diff main -- tests/test_telemetry_store.py` shows only ADDITIONS at file end, no modifications to existing 3 tests |
| Sprint 31.8 VACUUM tests unmodified | `git diff main -- tests/strategies/test_telemetry_store_vacuum.py` is empty |
| No sibling SQLite store touched | `git diff --name-only main` does not include any of the 7 sibling-store files listed in Constraints |
| `workflow/` submodule untouched | `git diff --name-only main -- workflow/` is empty |
| Full pytest green | `python -m pytest --ignore=tests/test_main.py -n auto -q` exits 0 |
| Vitest green | `cd argus/ui && npm test -- --run` exits 0 |
| Net pytest delta ≥ +6 | Closeout JSON `tests.new` ≥ 6 |

---

## Sprint-level escalation criteria (for `@reviewer`)

Trigger ESCALATE if ANY of:

- Phase A diagnostic produces no conclusive root cause; G1 fix shipped on speculation.
- `argus/data/migrations/evaluation.py` modified in any way.
- IMPROMPTU-10 lifecycle tests modified rather than appended.
- `RETENTION_DAYS` default in code is anything other than what the YAML config sets (silent default-divergence anti-pattern).
- VACUUM pre-headroom check has a bypass flag (RULE-039 non-bypassable validation).
- Health subfield writes to a different DB or namespace than `data/evaluation.db`.
- More than 6 files modified outside the explicit list (scope creep).
- Pytest or Vitest count regresses.
- DEC-389 written but DEF-234 not strikethrough (manifest discipline gap).

---

## Notes for the implementing Claude Code session

This sprint's narrative is unusual: Phase A is *required* before Phase B because we have a specific concrete unknown (why didn't the INFO log line fire on Apr 27→28). If Phase A produces a surprise (e.g., hypothesis H4 — "something else"), HALT after Phase A and surface findings to operator before proceeding. Do not ship a Phase B fix that doesn't address Phase A's root cause.

The operator-led conversation produced a clear empirical timeline that Phase A should reproduce:
- Apr 22 boot: 4,776 MB, freelist 0.0%, 0 retention log lines.
- Apr 23 boot: 9,294 MB, freelist 0.0%, 0 retention log lines.
- Apr 24 boot: 13,876 MB, freelist 0.0%, 0 retention log lines.
- Apr 27 boot: 18,328 MB, freelist 0.0%, 0 retention log lines.
- Apr 28 boot: 22,746 MB, **freelist 0.9%**, 0 retention log lines.

Freelist transition 0.0% → 0.9% on Apr 27→28 is the load-bearing evidence: pages were freed by SOME DELETE, but the INFO log line for that DELETE never fired. The Apr 27→28 boundary corresponds to Apr 20 rows aging out of the 7-day retention window for the first time. Phase A reproduces this with instrumented logging.

If Phase A confirms H1 (aiosqlite cursor.rowcount post-commit semantics), the fix is a 2-line change: capture `cursor.rowcount` BEFORE `await self._conn.commit()`, not after. If Phase A confirms H2, the fix is a logger-config touch in `argus/core/logging_config.py`. The impl prompt assumes H1 as the primary hypothesis but does not foreclose H2/H3.
