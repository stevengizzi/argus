# Sprint 31.91 — Session 2c.2 Close-Out

> **Track:** Side-Aware Reconciliation Contract (2a → 2b.1 → 2b.2 → 2c.1 → **2c.2** → 2d).
> **Position in track:** Fifth session. Adds 5-cycle auto-clear logic for the per-symbol entry gate engaged in Session 2c.1.

---

## ---BEGIN-CLOSE-OUT---

```json
{
  "session": "2c.2",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 4,
  "tests_total_after": 5163,
  "files_modified": [
    "argus/execution/order_manager.py",
    "argus/core/config.py",
    "config/system.yaml",
    "config/system_live.yaml",
    "tests/execution/order_manager/test_reconciliation_redesign.py",
    "tests/execution/order_manager/test_session2c2_phantom_short_auto_clear.py"
  ],
  "donotmodify_violations": 0,
  "tier_3_track": "side-aware-reconciliation",
  "m4_threshold_default": 5
}
```

---

## Self-Assessment

**CLEAR.** Spec executed exactly as written; no scope drift. The single
deviation from the spec's literal example pseudocode is structural rather
than semantic: the spec emits two near-identical INFO log lines for the
broker-zero and broker-LONG branches; the implementation collapses the
common counter-increment into a single statement and emits a
branch-specific log line so the runtime control flow is straight-line and
the two paths share their increment + threshold-check (eliminating the
duplication the spec's pseudocode flagged as the "long shares > 0" branch
that "is intentional, not a bug").

## Change Manifest

### `argus/core/config.py`
- Added `broker_orphan_consecutive_clear_threshold: int = 5` field on
  `ReconciliationConfig` with `ge=1, le=60` Pydantic bounds. The Field
  description explicitly documents the M4 cost-of-error asymmetry
  rationale ("false-clear is more dangerous than false-hold; raised from
  3 to 5 during Phase A revisit").

### `argus/execution/order_manager.py`
- Added `self._phantom_short_clear_cycles: dict[str, int] = {}` to
  `OrderManager.__init__()`, initialised next to the existing
  `_phantom_short_gated_symbols` set. The inline comment cites M4
  cost-of-error asymmetry verbatim.
- Added the auto-clear block to `reconcile_positions()` immediately after
  the existing Session 2b.1 broker-orphan LONG `resolved_symbols`
  cleanup. The block:
  1. Snapshots `_phantom_short_gated_symbols` via `list(...)` before
     iterating (mutation-during-iteration safety).
  2. For each gated symbol checks the current broker state:
     - **broker reports SHORT** (`broker_pos.side == OrderSide.SELL`) →
       resets the clear counter via `pop(symbol, None)` and logs an INFO
       reset line; gate stays engaged.
     - **broker reports zero** (`broker_pos is None`, i.e., absent from
       the dict) → increments counter and logs INFO `"broker reports
       zero shares"`.
     - **broker reports LONG** (`broker_pos.side == OrderSide.BUY`) →
       increments counter and logs INFO `"broker reports LONG shares=N,
       not short"`. This branch is intentional — original phantom-short
       condition has resolved; clearance is the correct response.
  3. When the counter reaches the configured threshold, the symbol is
     queued in `gated_to_clear`. After the iteration the gate is
     released (`discard`), the counter is removed (`pop`), the
     `_remove_gated_symbol_from_db` write is fire-and-forget via
     `asyncio.create_task` + tracked through
     `_pending_gate_persist_tasks` (matching Session 2c.1's persistence
     idiom), and a `logger.warning` records the auto-clear with cycle
     count.

### `config/system.yaml`, `config/system_live.yaml`
- Added explicit `broker_orphan_consecutive_clear_threshold: 5` under
  the `reconciliation:` block in both YAMLs, with a 4-line comment
  citing M4 cost-of-error asymmetry. **YAML override pattern:** both
  `system.yaml` (incubator/Alpaca path) and `system_live.yaml`
  (Databento + IBKR production path). The repo has only those two
  system YAMLs — there is no `system_paper.yaml` or `system_dev.yaml`,
  so the spec's "all three" listing collapses to "all two extant".

### `tests/execution/order_manager/test_reconciliation_redesign.py`
- Updated the `expected_keys` set in
  `test_reconciliation_config_fields_recognized` to include the new
  field. This test is a structural assertion that the model's
  `model_fields` matches the documented surface; without the update it
  would (and did) fail. Lock-step update is identical to how Session
  2c.1 extended the same set when adding
  `broker_orphan_entry_gate_enabled`.

### `tests/execution/order_manager/test_session2c2_phantom_short_auto_clear.py` (new)
- Four tests, all passing:
  1. `test_gate_clears_after_5_consecutive_zero_cycles` — DoD #6 (the
     positive auto-clear path; counter at 1..4 keeps the gate engaged,
     cycle 5 clears, DB row deleted).
  2. `test_gate_persists_through_transient_broker_zero_resets_counter` —
     DoD #5 (counter-reset-on-re-detection; cycle 1 zero → counter=1,
     cycle 2 short → reset, cycles 3..6 zero → counter=1..4, cycle 7 →
     gate clears).
  3. `test_clear_threshold_config_loadable_default_5` — DoD #6 (default
     value is 5; `config/system_live.yaml` sets it explicitly to 5).
  4. `test_clear_threshold_configurable_override` — DoD #7 (a 10-cycle
     override holds for 9 cycles and clears at 10; Pydantic bounds reject
     `=0` and `=61`).

## Judgment Calls

### J-1 — single increment site for the broker-zero / broker-LONG branches
The spec's pseudocode duplicates the counter-increment + threshold-check
across two near-identical branches. I collapsed those into a single
increment-then-log-then-check sequence keyed on `broker_pos is None` for
the log message only. Identical observable behaviour; eliminates a class
of "branches drift apart" bugs.

### J-2 — no `reset_daily_state()` change
The spec does not request that `_phantom_short_clear_cycles` be cleared
in `reset_daily_state`, and I did not add such a clear. The clear-cycles
counter is associated with the gate (which is persisted across restarts
via `data/operations.db`); resetting on EOD/start-of-day would force the
gate to re-accumulate 5 fresh cycles next session even after a
near-clear. That's intentional — the in-memory counter resetting at EOD
would be the safer/more-conservative posture, but it isn't what the spec
asked for, so I left it untouched and flag it here as a design point for
Tier 2 review.

### J-3 — fire-and-forget persistence via `_pending_gate_persist_tasks`
The auto-clear path schedules `_remove_gated_symbol_from_db` exactly the
way Session 2c.1's engagement path schedules `_persist_gated_symbol`,
including the same done-callback that calls `_log_persist_task_exception`
and removes the task from the tracking set. Tests await
`_pending_gate_persist_tasks` to drain before reading the DB; production
`reconcile_positions()` does not block on the write.

## Scope Verification

- [x] `_phantom_short_clear_cycles` state field initialised.
- [x] `broker_orphan_consecutive_clear_threshold: int = 5` config field
      added with `ge=1, le=60` bounds.
- [x] Auto-clear logic in reconciliation orphan-loop body (incrementing,
      reset on re-detection, threshold-clear, counter cleanup, fire-and-forget
      DB persistence).
- [x] Counter reset on re-detection verified (Test 2).
- [x] M4 5-cycle default verified (Test 3).
- [x] Configurability verified (Test 4).
- [x] 4 new tests; all passing.
- [x] Pytest baseline: 5,163 passed (target ≥ 5,138 met; +4 new tests in
      this session, the rest of the delta accumulated across earlier
      sub-sessions).
- [x] All do-not-modify list items show zero `git diff`.

## Regression Check

```
tests/execution/ + tests/core/test_session2b2_pattern_a.py:
  492 passed, 0 failed (scoped)

Full suite (--ignore=tests/test_main.py -n auto):
  5163 passed, 0 failed
  ~33 warnings (pre-existing categories — no new categories introduced)
```

Pre-existing warning categories unchanged: aiosqlite ResourceWarning
(DEF-192 (i)), pyarrow/xdist register_extension_type race fixed by
DEF-190 prewarm, async-mock-never-awaited residue (DEF-192 (ii)).

## Cited Evidence (Tier 2 Reviewer Anchors)

1. **M4 cost-of-error asymmetry — Field description** at
   `argus/core/config.py` (`ReconciliationConfig.broker_orphan_consecutive_clear_threshold.description`):
   > "Default 5 (~5 minutes) per M4 cost-of-error asymmetry: false-clear
   > is more dangerous than false-hold. Was 3 in earlier sprint drafts;
   > raised to 5 during Phase A revisit."

2. **M4 cost-of-error asymmetry — inline comment on the state field**
   in `OrderManager.__init__`:
   > "M4 cost-of-error asymmetry: 5 cycles (~5 min) > 3 cycles (~3 min)
   > because false-clear (gate releases while short persists) is more
   > dangerous than false-hold (gate stays engaged a few extra cycles)."

3. **YAML override pattern.** Both `config/system.yaml` and
   `config/system_live.yaml` carry an explicit
   `broker_orphan_consecutive_clear_threshold: 5` line with a 4-line
   comment header. The repo does not have `system_paper.yaml` or
   `system_dev.yaml`, so the override surface is two files, not three.

## CI / Context

- **Context state:** GREEN — well within budget; this session produced ~125
  net LOC of source/test changes plus a config update.
- **CI link:** to be filled in by Tier 2 reviewer once the branch is
  pushed; local baseline 5163 passed.

## Deferred Items

None opened in this session. The clear-counter resetting on
`reset_daily_state` is mentioned as a J-2 design point for Tier 2; it is
not opened as a DEF because the spec was deliberate about not requesting
it.

## Notes for Tier 2 Review

- The branch-collapse decision (J-1) is the only semantic deviation from
  the spec's pseudocode; it is observably equivalent. Reviewer should
  confirm by reading the post-edit `reconcile_positions` block and
  comparing against the spec.
- `_remove_gated_symbol_from_db` was a Session 2c.1 stub (Sprint 2c.1
  notes call it out as such); this session is the first call site, so
  the persistence side is now end-to-end.
- The `expected_keys` update in
  `test_reconciliation_config_fields_recognized` is mandatory — without
  it the model_fields-equality test fails. The lock-step update is the
  same pattern Session 2c.1 used.

## ---END-CLOSE-OUT---
