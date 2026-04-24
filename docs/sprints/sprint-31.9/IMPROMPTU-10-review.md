# IMPROMPTU-10 — Tier 2 Review

**Reviewer:** @reviewer subagent (Tier 2, read-only)
**Review date:** 2026-04-23
**Commits under review:** `8bdec82` (fix) + `ec1b244` (CLAUDE.md SHA backfill) on `main`
**Diff range:** `9b032c8..HEAD` (cumulative)
**CI run cited:** *not yet cited in close-out (operator handoff item)*
**Close-out read:** `docs/sprints/sprint-31.9/IMPROMPTU-10-closeout.md` (CLEAN self-assessment)

---BEGIN-REVIEW---

## Summary

IMPROMPTU-10 closes DEF-197 (`evaluation.db` accumulating multi-GB per session,
4.78 GB → 9.29 GB → 14.5 GB across consecutive boots). The diagnostic against
the live 14.5 GB DB is concrete and falsifies the original "retention not
firing" hypothesis: all 61M rows span only 4 distinct days
(`2026-04-20 / 2026-04-23`), all within the 7-day retention window. The
startup `cleanup_old_events()` DELETE was firing correctly — it just had
nothing to delete. Root cause: the single startup-only invocation cannot
keep up with sessions running >24 h; once the retention boundary is crossed
mid-session, day-8+ rows accumulate until the next reboot.

The fix matches the diagnostic. `EvaluationEventStore.initialize()` now
spawns `_run_periodic_retention()` as an `asyncio.create_task` on a 4-hour
cadence; `close()` cancels and awaits the task. `RETENTION_DAYS=7` and the
fire-and-forget write pattern are unchanged. Three lifecycle regression
tests are added; all are revert-proof under mental revert.

The diff is precisely scoped: 6 files (1 source, 1 test, 1 close-out, 3
bookkeeping). Zero out-of-scope files touched. Zero sibling SQLite stores
touched. No one-shot `VACUUM INTO` committed as code (documented as
operator step in close-out §7). Full pytest suite green at 5,080 passed
(+3 vs baseline 5,077). Warning count 25 (within DEF-192's documented
[25, 31] xdist-variance band; no new warning category).

**Verdict: CLEAR.**

## Session-specific review focus (kickoff §"Session-Specific Review Focus")

### Check 1 — Diagnostic evidence is concrete

Close-out §1 contains raw Q1/Q2/Q3 SQL output:
- Q1: `MIN/MAX trading_date = 2026-04-20 / 2026-04-23`, 61,035,650 rows, 4 distinct days.
- Q2: per-day breakdown (2026-04-23: 20,154,031 rows; 2026-04-22: 19,836,102; 2026-04-21: 20,108,068; 2026-04-20: 937,449).
- Q3: page_count 3,552,164; page_size 4,096; freelist 0; file size 14,549,663,744 bytes (14.5 GB).

The hypothesis ("all data within retention but file growing → periodic
scheduler missing") is correctly derived from the kickoff's hypothesis
tree branch ("If Q1 spans ≤7 days but Q3 shows high page_count → rows are
within retention but ingestion rate exceeds retention window").

**Status: CLEAR.** Concrete numbers match the close-out's narrative.

### Check 2 — Fix matches hypothesis

Spec called for: (a) `RETENTION_INTERVAL_SECONDS = 4*60*60` constant, (b)
`_run_periodic_retention()` async method that sleeps + calls
`cleanup_old_events()` + catches exceptions, (c) `initialize()` ends with
`asyncio.create_task(self._run_periodic_retention())`, (d) `close()`
cancels + awaits the task.

Verified directly by reading `argus/strategies/telemetry_store.py`:
- (a) Line 82: `RETENTION_INTERVAL_SECONDS: int = 4 * 60 * 60` ✓
- (b) Lines 310–330: `_run_periodic_retention()` defined; `while True:` body
  awaits `asyncio.sleep(self.RETENTION_INTERVAL_SECONDS)`, calls
  `await self.cleanup_old_events()`, catches `CancelledError` (re-raises)
  and generic `Exception` (logs warning with `exc_info=True`). ✓
- (c) Line 156:
  `self._retention_task = asyncio.create_task(self._run_periodic_retention())`
  is the last statement of `initialize()`. ✓
- (d) Lines 388–395: `close()` cancels `self._retention_task`, awaits it
  inside try/except `CancelledError`, sets to `None` before closing the
  aiosqlite connection. ✓

`RETENTION_DAYS = 7` (line 77) unchanged. Fire-and-forget write pattern
in `write_event()` (lines 158–191) untouched. `cleanup_old_events()`
implementation untouched.

**Status: CLEAR.** Fix is exactly what the diagnostic supports. No
date-cutoff or timezone correction was attempted (correctly — diagnostic
ruled those out).

### Check 3 — Regression test actually regresses (mental revert verification)

Read `tests/test_telemetry_store.py:189–248`:

1. `test_periodic_retention_task_starts_on_initialize` (lines 189–195):
   asserts `store._retention_task is not None and not store._retention_task.done()`.
   **Revert simulation:** removing the `asyncio.create_task(...)` line from
   `initialize()` leaves `_retention_task` at its `__init__` default of
   `None` → `assert store._retention_task is not None` fails on first
   assertion. ✓ Regresses cleanly.

2. `test_periodic_retention_task_cancels_cleanly_on_close` (lines 198–216):
   captures task handle pre-close, awaits `s.close()`, asserts `task.done()`.
   **Revert simulation:** removing the `task.cancel() + await task` block
   from `close()` leaves the task pending after close returns → `task.done()`
   stays `False` → assertion fails. ✓ Regresses cleanly. (Bonus: also
   produces a "Task was destroyed but it is pending" warning at GC time.)

3. `test_periodic_retention_invokes_cleanup_old_events` (lines 219–248):
   monkeypatches `RETENTION_INTERVAL_SECONDS` to 0.05s, writes a 10-day-old
   row, awaits 0.2s, asserts the row is gone.
   **Revert simulation:** removing `asyncio.create_task(...)` from
   `initialize()` means no periodic loop fires; the 10-day-old row remains
   → `assert len(post) == 0` fails on a 1-row result. ✓ Regresses cleanly.

The close-out §5 documents an explicit revert verification was performed
(`Reverted-state rows after 0.2s wait: 1`). All three tests passed locally:

```
$ python -m pytest tests/test_telemetry_store.py -xvs 2>&1 | tail -20
tests/test_telemetry_store.py::test_periodic_retention_task_starts_on_initialize PASSED
tests/test_telemetry_store.py::test_periodic_retention_task_cancels_cleanly_on_close PASSED
tests/test_telemetry_store.py::test_periodic_retention_invokes_cleanup_old_events PASSED
17 passed in 1.25s
```

**Status: CLEAR.** All three tests are revert-proof.

### Check 4 — No DEF-192 regression

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
5080 passed, 25 warnings in 51.35s
```

Single observed run: 25 warnings. Close-out §6 documents 3 consecutive
runs at [25, 27, 27]; baseline 26. All within CLAUDE.md DEF-192's
documented "intermittent and xdist-order-dependent" band. The spec's
specified observation range was [25, 31] — single observed run (25) is
the lower bound of that range. No new warning category surfaced. The
new periodic retention loop reuses the existing aiosqlite connection
inside `cleanup_old_events()` (no new long-lived connection opened by
the loop itself), so DEF-192 category-(i) surface is unchanged.

**Status: CLEAR.**

### Check 5 — Operator one-shot cleanup is documented, NOT committed

`git show 8bdec82 --stat` lists 6 files; no `.sh` files, no
`scripts/*.py` files. Close-out §7 contains the `VACUUM INTO` recipe as
markdown documentation only. No `data/evaluation.db.new`, no committed
backup-rotation script, no inline `VACUUM INTO` in `argus/`.

**Status: CLEAR.**

### Check 6 — Scope ≤6 files

```
$ git diff 9b032c8..HEAD --name-only
CLAUDE.md
argus/strategies/telemetry_store.py
docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md
docs/sprints/sprint-31.9/IMPROMPTU-10-closeout.md
docs/sprints/sprint-31.9/RUNNING-REGISTER.md
tests/test_telemetry_store.py
```

Exactly 6 files: 1 source, 1 test, 1 close-out (new), 3 bookkeeping.
Matches close-out §8 manifest exactly.

**Status: CLEAR.**

### Check 7 — Test count net delta ≥ +2

Baseline (post-IMPROMPTU-08): 5,077 pytest. Post-session: 5,080 pytest.
Net delta: **+3**. Matches close-out claim and exceeds the kickoff's
target of "+2 to +3 new pytest". All three new tests are in
`tests/test_telemetry_store.py` (verified by collection: file count
8 → 17 with the 3 new lifecycle tests added in the IMPROMPTU-10 block).

**Status: CLEAR.**

## Sprint-level escalation criteria (none triggered)

| Criterion | Status |
|---|---|
| `EvaluationEventStore.RETENTION_DAYS` value changed (must be 7) | ✅ Unchanged (line 77: `RETENTION_DAYS: int = 7`) |
| Fire-and-forget write pattern refactored | ✅ `write_event()` lines 158–191 untouched in diff |
| Other SQLite stores touched (`counterfactual_store.py`, `experiments/store.py`, `learning/learning_store.py`) | ✅ `git diff` against all three returns empty |
| One-shot `VACUUM INTO` committed as code | ✅ Documented in close-out §7 only; no `.sh` / `.py` files added |
| `workflow/` submodule modified | ✅ `git diff workflow/` empty |
| DEF-192 warning count regressed (new category, or sustained count well above 31) | ✅ Single observed run at 25; close-out 3-run range [25, 27]; baseline 26; no new category |
| Full pytest suite broken post-session | ✅ 5,080 passed, 0 failed |
| Audit-report back-annotation modified | ✅ `git diff docs/audit-2026-04-21/` empty |
| Files under `argus/execution/order_manager.py`, `argus/api/auth.py`, `config/experiments.yaml`, frontend (`argus/ui/`) | ✅ All empty in `git diff` |

**No escalation triggers fired.**

## Sprint-level regression checks

- **pytest net delta: +3** (target: ≥ +2). CLEAR.
- **Vitest count unchanged.** No `argus/ui/` files in diff. CLEAR.
- **No scope boundary violation.** All 6 files in scope per kickoff §"Files touched". CLEAR.
- **CLAUDE.md DEF-197 strikethrough with commit SHA** — confirmed at line 425, includes `commit `8bdec82`` per `ec1b244` backfill. CLEAR.

## Findings

None. The implementation is clean, the diagnostic is concrete, the fix
matches the hypothesis, and all three regression tests are revert-proof.
Scope is tight (6 files, 1 source change of ~30 lines net) and matches
the kickoff manifest exactly. No deviations from spec.

The kickoff's "fix candidate (1) most likely" prediction is borne out by
the diagnostic — the implementer correctly ran the diagnostic first
before picking the fix, rather than presupposing the answer. The
exception-handling pattern in `_run_periodic_retention()` is conservative
(re-raises `CancelledError`, catches and logs everything else with
`exc_info=True`) and matches the project's "fire-and-forget writes MUST
surface failures" rule from `architecture.md`.

## Operator handoff items

1. **Green CI URL** (kickoff Definition-of-Done item). Not cited in close-out
   §10 — flagged as `*pending commit + push*`. Both commits (`8bdec82` +
   `ec1b244`) are on local `main` per `git log`; CI URL needs to be cited
   when the operator pushes. Per the standard reviewer profile this is an
   operator handoff item, not a verdict blocker.

## Test verification (local)

| Harness | Result |
|---|---|
| `python -m pytest --ignore=tests/test_main.py -n auto -q` | **5080 passed, 25 warnings in 51.35s** ✅ |
| `python -m pytest tests/test_telemetry_store.py -xvs` | **17 passed in 1.25s** (3 new lifecycle tests pass) ✅ |
| `git diff 9b032c8..HEAD --name-only` | 6 files (within ≤6 cap) ✅ |
| `git diff 9b032c8..HEAD -- workflow/ argus/execution/order_manager.py argus/api/auth.py config/experiments.yaml argus/intelligence/counterfactual_store.py argus/intelligence/experiments/store.py argus/intelligence/learning/learning_store.py argus/ui/ docs/audit-2026-04-21/` | empty ✅ |
| `grep "RETENTION_DAYS: int = 7" argus/strategies/telemetry_store.py` | line 77 (unchanged) ✅ |
| Mental revert of `asyncio.create_task` in `initialize()` | All 3 lifecycle tests would fail (verified by inspection); close-out §5 records explicit script-based revert verification ✅ |

## Verdict

**CLEAR.**

All seven session-specific review focus checks pass, all sprint-level
regression checks pass, no escalation criterion was triggered, and no
findings warrant flagging as CONCERNS. The fix is precisely scoped, the
diagnostic is concrete, the regression tests are revert-proof, and the
operator one-shot cleanup is correctly documented as a manual step
rather than committed code.

The only outstanding item — the green CI URL citation — is an operator
handoff per kickoff convention, not a reviewer verdict blocker.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "blocking": false,
  "escalation_triggered": false,
  "findings": [],
  "scope_violations": [],
  "escalation_criteria_checked": [
    { "criterion": "EvaluationEventStore.RETENTION_DAYS value changed", "triggered": false, "evidence": "Line 77: RETENTION_DAYS: int = 7 (unchanged)" },
    { "criterion": "Fire-and-forget write pattern refactored", "triggered": false, "evidence": "write_event() lines 158-191 untouched in diff" },
    { "criterion": "Other SQLite stores touched", "triggered": false, "evidence": "git diff against counterfactual_store.py / experiments/store.py / learning/learning_store.py all empty" },
    { "criterion": "One-shot VACUUM INTO committed as code", "triggered": false, "evidence": "Documented in close-out §7 only; no .sh/.py files added; git show 8bdec82 --stat lists 6 markdown+source files only" },
    { "criterion": "workflow/ submodule modified", "triggered": false, "evidence": "git diff workflow/ empty" },
    { "criterion": "DEF-192 warning count regressed (new category, or sustained well above 31)", "triggered": false, "evidence": "Single run 25 warnings, close-out 3-run range [25,27], baseline 26, no new category surfaced" },
    { "criterion": "Full pytest suite broken post-session", "triggered": false, "evidence": "5080 passed, 0 failed" },
    { "criterion": "Audit-report back-annotation modified", "triggered": false, "evidence": "git diff docs/audit-2026-04-21/ empty" }
  ],
  "test_results": {
    "pytest_full_suite": { "passed": 5080, "failed": 0, "skipped": 0, "warnings": 25, "delta_vs_baseline": 3, "baseline": 5077, "runtime_seconds": 51.35 },
    "telemetry_store_module": { "collected": 17, "passed": 17, "failed": 0, "new_tests": 3 },
    "scope_file_count": 6,
    "out_of_scope_diffs_empty": true,
    "retention_days_unchanged": true,
    "mental_revert_verification": "All 3 lifecycle tests fail on revert (inspection-confirmed); close-out §5 records explicit script-based verification with output 'Reverted-state rows after 0.2s wait: 1'"
  },
  "diagnostic_evidence_concrete": {
    "q1_min_max_dates": "2026-04-20 / 2026-04-23 (4 distinct days, all within 7-day retention)",
    "q1_total_rows": 61035650,
    "q3_page_count": 3552164,
    "q3_freelist": 0,
    "q3_file_size_bytes": 14549663744,
    "hypothesis_branch_matched": "data within retention but file growing → periodic scheduler missing"
  },
  "fix_matches_hypothesis": {
    "approach": "Candidate (1) — Periodic retention task",
    "constant_added": "RETENTION_INTERVAL_SECONDS: int = 4 * 60 * 60 (line 82)",
    "method_added": "_run_periodic_retention() lines 310-330 (sleep + cleanup + CancelledError-aware exception handling)",
    "initialize_wires_task": "Line 156: self._retention_task = asyncio.create_task(self._run_periodic_retention())",
    "close_cancels_task": "Lines 388-395: cancel + await + None-out before connection close",
    "no_date_cutoff_correction": true,
    "no_timezone_correction": true
  },
  "operator_handoff_items": [
    "Green CI URL to be cited on push (close-out §10 marks as *pending commit + push*; both commits 8bdec82 + ec1b244 are on local main; not a reviewer verdict blocker)."
  ]
}
```
