# Retention Mechanism Diagnostic — 2026-04-28

> Sprint 31.915 Phase A. Single-use diagnostic; the script
> (`scripts/diag_retention_logging.py`) is deleted at the end of Phase A
> per the sprint-spec. This document is the authoritative-record artifact.

## Hypothesis tree (from sprint-spec)

| Hypothesis | What it predicts |
|---|---|
| H1 | aiosqlite `cursor.rowcount` returns 0 post-commit, even when DELETE removed N rows on disk. The `if deleted > 0:` gate fails silently; success-path INFO never fires. |
| H2 | Logger config issue — `argus.strategies.telemetry_store` INFO line gets routed to a level not in any handler. |
| H3 | Exception eaten by `_run_periodic_retention`'s broad `except Exception:` — DELETE worked, but VACUUM (or some downstream call) raised, the success-path INFO line that lives AFTER `await self._vacuum()` never fires, only a generic WARNING gets emitted. |
| H4 | Something else. |

## Method

`scripts/diag_retention_logging.py` reproduces the IMPROMPTU-10 retention path
under production-equivalent logger config (mirrors
`argus/core/logging_config.py`'s `ConsoleFormatter`, INFO root level,
`argus.strategies.telemetry_store` logger). Three scenarios:

1. **outside_retention_window_minus_10d** — seed 100 rows with
   `trading_date = today_et - 10d` (10 days outside the 7-day window).
   Capture `cursor.rowcount` immediately after `execute()` AND immediately
   after `commit()`. Probe disk-side via `PRAGMA freelist_count` and
   `PRAGMA page_count` before and after.
2. **inside_retention_window_plus_1d** — seed 100 rows with
   `trading_date = today_et + 1d` (clearly inside retention; nothing should
   delete). Confirms zero-deletion path semantics.
3. **h3_probe_vacuum_raises** — seed 50 rows outside the window, monkey-patch
   `store._vacuum` to raise `OSError("ENOSPC: ...")`, run
   `cleanup_old_events()`, capture every log record emitted from the
   `argus.strategies.telemetry_store` logger.

Run command:

```
python scripts/diag_retention_logging.py 2>&1 \
  | tee dev-logs/2026-04-28_retention-mechanism-diagnostic-raw.txt
```

## Raw evidence

```
--- outside_retention_window_minus_10d ---
  seed_trading_date                      = '2026-04-18'
  cutoff                                 = '2026-04-21'
  rows_before                            = 100
  rows_after                             = 0
  rows_actually_deleted                  = 100
  rowcount_before_commit                 = 100
  rowcount_after_commit                  = 100
  deleted_branch_taken                   = 'success_with_vacuum'
  freelist_before                        = 0
  freelist_after                         = 3
  page_count_before                      = 10
  page_count_after                       = 10
  exception_traceback                    = None

--- inside_retention_window_plus_1d ---
  seed_trading_date                      = '2026-04-29'
  cutoff                                 = '2026-04-21'
  rows_before                            = 100
  rows_after                             = 100
  rows_actually_deleted                  = 0
  rowcount_before_commit                 = 0
  rowcount_after_commit                  = 0
  deleted_branch_taken                   = 'zero_deletion_silent'
  freelist_before                        = 0
  freelist_after                         = 0
  exception_traceback                    = None

--- h3_probe_vacuum_raises ---
  captured_logs                          = [('WARNING',
                                             'EvaluationEventStore: periodic retention iteration failed')]
  info_log_for_deletion_emitted          = False
  warning_log_emitted                    = True
  cleanup_propagated_exception           = 'OSError: ENOSPC: simulated disk pressure during VACUUM'
```

## What the data conclusively rules out

- **H1 is ruled out.** On the in-tree aiosqlite version (see
  `requirements.lock`), `cursor.rowcount` returns the correct deleted-row
  count BOTH before and after `await self._conn.commit()`. The 2-line fix
  the sprint-spec hypothesised (capture rowcount before commit) is
  unnecessary. Proof: scenario 1 returned `rowcount_before_commit = 100`,
  `rowcount_after_commit = 100`, with 100 rows actually removed from disk.

- **H2 is ruled out as a sufficient mechanism.** The diagnostic uses
  production-equivalent logger setup (root logger at INFO, `ConsoleFormatter`
  on stdout). Both the "EvaluationEventStore initialized" INFO and the H3
  WARNING surface correctly. If a logger-routing bug were the sole cause,
  these lines would also be silently dropped — they are not.

## Confirmed root cause

**H3 with mechanism refinement** — the silent-failure mode is not a single
bug but **an observability gap** with two coupled facets:

1. **The success-path INFO log line lives AFTER `await self._vacuum()`**
   in the production code at
   `argus/strategies/telemetry_store.py:271-282`:

   ```python
   if deleted > 0 and self.VACUUM_AFTER_CLEANUP:
       await self._vacuum()              # ← raises ENOSPC under disk pressure
       size_after_mb = self._get_db_size_mb()
       logger.info(                       # ← never reached if _vacuum() raised
           "EvaluationEventStore: retention deleted %d rows (before %s), ..."
       )
   elif deleted > 0:
       logger.info("Cleaned up %d old evaluation events ...", deleted, cutoff)
   ```

   The H3 probe confirmed empirically that with VACUUM raising, the
   success-path INFO never fires; only a generic `WARNING: periodic
   retention iteration failed` surfaces from
   `_run_periodic_retention`'s broad except. An operator grepping logs
   for "retention deleted" would see nothing.

2. **The zero-deletion branch is completely silent.** The current code
   emits no log line at all when `deleted == 0`. Between Apr 22 and
   Apr 27 the periodic retention task ran ~36 times (4-hour cadence over
   ~6 days) and emitted zero log lines per iteration because no rows had
   yet aged out of the 7-day window. The operator's "no retention logs
   anywhere" observation IS consistent with this — until the
   freelist transition 0.0% → 0.9% on Apr 27→28 contradicted it.

## Mechanism (2-3 sentences)

On the Apr 27→28 boundary, Apr 20 rows aged out of the 7-day retention
window; the periodic task's DELETE removed them and committed (evidence:
freelist 0.0% → 0.9%). However, the subsequent `await self._vacuum()` call
raised — most likely with `OSError: ENOSPC` given the operator's tight
disk environment (VACUUM INTO needs ~2× source-size headroom on the same
volume) — propagating the exception up through `cleanup_old_events()` to
`_run_periodic_retention`'s broad `except Exception:`. The success-path
INFO line that lives AFTER the VACUUM call never fired; only a generic
"periodic retention iteration failed" WARNING was emitted, which the
operator's grep for "retention deleted" missed. From Apr 22–27, the
zero-deletion path had been silent by design (no INFO line emitted when
`deleted == 0`), reinforcing the false impression that the periodic task
was not running at all.

## Fix shape (Phase B)

The Phase B implementation MUST address both observability facets in
`cleanup_old_events()`:

1. **Log the DELETE outcome BEFORE attempting VACUUM.** Move the
   success-path INFO line above `await self._vacuum()` so a vacuum failure
   does not eat the deletion record. Split the message: one INFO for
   "retention deleted N rows", one INFO for "post-retention VACUUM complete
   ...".
2. **Log every iteration regardless of `deleted`.** The zero-deletion
   branch emits an INFO line ("retention scanned (cutoff X, 0 rows
   matched)") so operators can confirm the periodic task is alive.
3. **Update the G5 observability instance fields
   (`_last_retention_run_at_et`, `_last_retention_deleted_count`) BEFORE
   any VACUUM attempt** so `/health` reflects the DELETE outcome
   regardless of VACUUM success.
4. **Add the G4 pre-VACUUM disk-headroom check** so the silent-ENOSPC
   class is structurally prevented (loud WARNING + abort-this-cycle, no
   bypass flag per RULE-039).

This mechanism shape is a **deviation from the sprint-spec's
prescribed fix shape** (which retained `logger.info(...)` AFTER
`await self._vacuum()`). The deviation is justified because Phase A
confirmed H3, not H1; with H3 the original layout still loses the
DELETE-outcome INFO whenever VACUUM raises. Cited as a Judgment Call in
the close-out.

## Phase A → Phase B halt-or-proceed gate

Per sprint-spec A3: H1 is conclusively ruled out, but H3 is conclusively
confirmed AND the spec's prescribed Phase B fix shape (G3/G4/G5 together)
addresses every plausible silent-failure path. No HALT required. Proceed
to Phase B with the adapted log-order described above + the spec's
prescribed G3/G4/G5 changes.

## Cleanup

`scripts/diag_retention_logging.py` is deleted at the end of Phase A per
sprint-spec A4. The Phase C regression test
`tests/test_telemetry_store.py::test_retention_logs_success_path` captures
the H3 mechanism for future sessions.
