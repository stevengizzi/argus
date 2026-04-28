# Sprint 31.91 Session 2c.1 — Close-Out Report

> **Track:** Side-Aware Reconciliation Contract (Sessions 2a → 2b.1 → 2b.2 → **2c.1** → 2c.2 → 2d).
> **Self-assessment:** **CLEAN** (PROPOSED_CLEAR pending Tier 2 verdict).
> **Context State:** GREEN.

---

## Verdict JSON

```json
{
  "session": "2c.1",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 6,
  "tests_total_after": 5159,
  "files_modified": [
    "argus/core/config.py",
    "argus/execution/order_manager.py",
    "argus/main.py",
    "config/system.yaml",
    "config/system_live.yaml",
    "tests/execution/order_manager/test_session2c1_phantom_short_gate.py",
    "tests/execution/order_manager/test_reconciliation_redesign.py"
  ],
  "donotmodify_violations": 0,
  "main_py_scoped_exception": "M5 rehydration insertion before order_manager.start() (which subscribes to OrderApprovedEvent) at argus/main.py:1066-1080; plus operations_db_path kwarg at the OrderManager construction at line 1065",
  "tier_3_track": "side-aware-reconciliation"
}
```

---

## Change Manifest

### `argus/core/config.py`
- Added `ReconciliationConfig.broker_orphan_entry_gate_enabled: bool = True`
  with a `Field(default=True, description=...)` declaration. Default `True`
  matches production-safe behavior; setting to `False` keeps the alert
  but disables the entry gate (operator-only mitigation mode).

### `argus/execution/order_manager.py`
- New imports: `from pathlib import Path`, `import aiosqlite`.
- New module-level helper `_log_persist_task_exception(task, symbol)` —
  done-callback that surfaces fire-and-forget persistence failures via
  WARNING (DEC-345 fire-and-forget pattern requires visible failure).
- New `OrderManager.__init__()` parameter: `operations_db_path: str | None = None`
  (defaults to `"data/operations.db"` if None).
- New instance state:
  - `self._phantom_short_gated_symbols: set[str] = set()`
  - `self._operations_db_path: str = ...`
  - `self._pending_gate_persist_tasks: set[asyncio.Task[None]] = set()`
    (tracks fire-and-forget persist tasks so the GC doesn't reap them
    pre-completion; tasks remove themselves in their done-callback).
- `_handle_broker_orphan_short()` extended (Session 2b.1's handler):
  after the existing alert emission, when
  `reconciliation_config.broker_orphan_entry_gate_enabled` is True AND
  `symbol not in self._phantom_short_gated_symbols`, the symbol is added
  to the in-memory set, an `asyncio.create_task` writes the row, and a
  CRITICAL log line announces the engagement. The `not in` guard is
  the structural enforcement of idempotency (re-detection of an
  already-gated symbol does NOT re-write or re-log).
- `on_approved()` extended: at the TOP of the handler (after the
  signal-None guard, before any other logic), if
  `signal.symbol in self._phantom_short_gated_symbols`, a
  `SignalRejectedEvent(rejection_stage="risk_manager",
  rejection_reason="phantom_short_gate", metadata={"gate":
  "phantom_short_gate", "symbol": ..., "reason_detail": ...})` is
  published, a CRITICAL log line is emitted, and the handler returns
  before any broker work. Mirrors DEC-367 margin-circuit ordering.
- New methods on `OrderManager`:
  - `_PHANTOM_SHORT_GATED_SYMBOLS_DDL` — class-level DDL constant.
  - `_ensure_operations_db_parent()` — sync helper to mkdir parent if
    missing (aiosqlite.connect creates the file but not the parent).
  - `async _persist_gated_symbol(symbol, source, last_observed_short_shares=None)` —
    `INSERT OR REPLACE` upsert with `engaged_at_utc` / `engaged_at_et` /
    `engagement_source` / `last_observed_short_shares` columns. Atomic
    by SQLite default; `await db.commit()` on success path.
  - `async _remove_gated_symbol_from_db(symbol)` — `DELETE WHERE symbol = ?`
    (Session 2c.1 stub; called by Session 2c.2 auto-clear and Session 2d
    operator override).
  - `async _rehydrate_gated_symbols_from_db()` — M5 rehydration. Creates
    the table idempotently, loads all rows into the in-memory set, logs
    CRITICAL when symbols are restored.

### `argus/main.py`
- Single scoped block per invariant 15 exception:
  - Pass `operations_db_path=str(Path(config.system.data_dir) / "operations.db")`
    to the existing `OrderManager(...)` construction at line 1065.
  - Insert `await self._order_manager._rehydrate_gated_symbols_from_db()`
    immediately BEFORE the existing `await self._order_manager.start()`
    line. `start()` is what subscribes to `OrderApprovedEvent`, so the
    rehydration call satisfies the M5 ordering requirement.

### `config/system.yaml`, `config/system_live.yaml`
- Added `broker_orphan_entry_gate_enabled: true` under the
  `reconciliation:` section in both YAMLs.

### `tests/execution/order_manager/test_session2c1_phantom_short_gate.py` (NEW)
- 6 tests, mapped 1:1 to the Session 2c.1 spec's "Tests" section:
  1. `test_phantom_short_gate_engages_on_broker_orphan_short` —
     engagement via reconciliation; SQLite row written; idempotent
     re-detection (no duplicate row, set unchanged).
  2. `test_gate_blocks_order_approved_for_gated_symbol` — gated symbol
     produces `SignalRejectedEvent(rejection_reason="phantom_short_gate")`;
     `broker.place_bracket_order` is NOT awaited.
  3. `test_gate_does_not_block_other_symbols` — per-symbol granularity;
     gating AAPL does not block MSFT (broker IS awaited for MSFT).
  4. `test_phantom_short_gated_symbols_persist_to_sqlite` — full row
     payload check (all 5 columns populated correctly).
  5. `test_gate_state_rehydrated_on_restart_before_event_processing` —
     M5 ordering: state populated AFTER rehydrate AND BEFORE start();
     OrderApprovedEvent published after subscribe is rejected without
     reaching the broker.
  6. `test_gate_state_survives_argus_restart_blocks_entries` — E2E:
     instance A engages → drop A → instance B rehydrates → still gated.

### `tests/execution/order_manager/test_reconciliation_redesign.py`
- `test_reconciliation_config_fields_recognized` updated: added
  `broker_orphan_entry_gate_enabled` to `expected_keys`. Comment
  updated. No behavioral change to the test logic.

---

## Cited details (per spec close-out checklist)

- **`main.py` line range of the rehydration insertion:** `argus/main.py:1066-1080`.
  The `operations_db_path` kwarg lives at `1066-1068`; the rehydrate call
  + comment block lives at `1071-1080`. Existing `await self._order_manager.start()`
  remains at line `1081` immediately after.

- **Was `data/operations.db` created or extended?** Created. No
  pre-existing `operations.db` file or table existed
  (grep-verified at session start). Session 2c.1 introduces the file
  and the `phantom_short_gated_symbols` table via idempotent
  `CREATE TABLE IF NOT EXISTS` on first read/write.

- **aiosqlite usage pattern matched:** Per-write connection lifecycle
  (mirrors `argus.intelligence.experiments.store` — the dominant
  pattern in the codebase, e.g.,
  `async with aiosqlite.connect(db_path) as db: ...`). Per RULE-007 we
  did NOT introduce a new connection-pooling pattern.

---

## Definition of Done — verified

- [x] `_phantom_short_gated_symbols` state field initialized.
- [x] Gate engagement in `_handle_broker_orphan_short` (Session 2b.1
      handler extended); idempotent (`not in` guard + `INSERT OR REPLACE`).
- [x] `on_approved` handler rejects gated symbols with
      `rejection_reason="phantom_short_gate"`.
- [x] Per-symbol granularity verified (Test 3: MSFT not blocked when
      AAPL is gated).
- [x] `phantom_short_gated_symbols` SQLite table created in
      `data/operations.db` (path resolved from `config.system.data_dir`).
- [x] M5 rehydration ordering: `_rehydrate_gated_symbols_from_db()`
      runs BEFORE `order_manager.start()` (which is the subscription
      point) in main.py.
- [x] `broker_orphan_entry_gate_enabled: bool = True` config field added.
- [x] DEC-367 margin-circuit state independence verified (no shared
      state; both gates fire independently when both apply — see
      "Sprint-Level Regression Checklist" below).
- [x] 6 new tests; all passing.
- [x] Full suite: **5,159 passing** (target ≥ 5,134; baseline 5,153 + 6 = 5,159).
- [x] All do-not-modify list items show zero `git diff` (with the
      scoped main.py exception).
- [ ] Tier 2 review verdict CLEAR — pending.

---

## Sprint-Level Regression Checklist

| Invariant | Status | Notes |
|---|---|---|
| 5 (test baseline) | PASS | 5,153 → 5,159 (+6 new tests). Above ≥ 5,134 target. |
| 9 (IMPROMPTU-04 startup invariant unchanged) | PASS | `argus/main.py:194-204` (the IMPROMPTU-04 fix region) is untouched. The 2c.1 edit lives at `argus/main.py:1066-1080` and only adds the rehydrate call + the operations_db_path kwarg. |
| 10 (DEC-367 margin circuit unchanged) | PASS | `_margin_circuit_open` / `_margin_rejection_count` paths in `on_approved` and `on_cancel` are unmodified. The phantom-short gate check is positioned at the top of `on_approved` BEFORE the margin-circuit check; both gates are independent set-membership tests on the symbol. A symbol present in both rejects via the phantom-short branch first. |
| 14 (alert/gate/persistence row "After Session 2c.1") | PASS | Recon detects shorts = "full (alert + gate + persistence)". The 2c.1 contribution is the gate + persistence; 2b.1 contributed alert. |
| 15 (main.py edit scope, scoped exception) | PASS with documented exception | Session 2c.1 adds 11 lines to `main.py` immediately around the existing `OrderManager` construction + start. The diff is the `operations_db_path` kwarg (3 lines) + the M5 rehydrate-before-start block (8 lines, inclusive of comment). No edits in the IMPROMPTU-04 startup-invariant region. |

---

## Judgment Calls

1. **Stub `_remove_gated_symbol_from_db()` in 2c.1 even though 2c.2 / 2d
   are the call sites.** The spec lists both methods; implementing the
   delete now keeps the SQL surface complete and avoids forcing 2c.2 /
   2d to re-touch this region. The method has no in-tree caller in
   2c.1; tests do not exercise it. Documented in the docstring.

2. **`_pending_gate_persist_tasks` set added beyond the spec.** The
   spec describes a fire-and-forget `asyncio.create_task` without
   tracking. Without tracking, two issues surface in tests AND in
   production: (a) the GC may reap the task before its done-callback
   fires (Python 3.11 keeps a weak reference only) and (b) tests need
   to await the task to read the DB without racing it. The set is
   small (one entry per concurrent persist; phantom-short is rare),
   tasks remove themselves in the done-callback, and the helper
   protects against both issues. Not user-visible behavior change;
   pure infrastructure.

3. **`rejection_reason="phantom_short_gate"` flat string vs descriptive
   sentence.** The spec literally says `reason="phantom_short_gate"`;
   the existing margin-circuit pattern uses a descriptive sentence
   like `"Margin circuit breaker open — N rejections this session"`.
   Used the literal flat code per spec, with the descriptive detail
   in `metadata["reason_detail"]`. This makes the rejection code
   programmatically distinguishable and analytics-friendly; the
   detail is structured rather than a substring of a free-form
   message. Pre-existing margin-circuit pattern is unchanged.

4. **`rejection_stage="risk_manager"`.** DEF-177 is open: `RejectionStage`
   enum is missing both `MARGIN_CIRCUIT` and `phantom_short_gate`
   distinct values. Per RULE-007 we did NOT extend the enum here —
   that work is gated to a dedicated cross-domain session. Mirrored
   the existing margin-circuit pattern of overloading `"risk_manager"`.
   Filed as same-family follow-on (DEF-177 already covers the cross-
   domain split needed to clean both rejection codes).

5. **Skipping persistence write on idempotent re-detection.** Spec
   notes that `INSERT OR REPLACE` would also be idempotent on the SQL
   side, but we skip the write entirely via the `not in` guard. This
   avoids unnecessary I/O when a phantom short persists across
   reconciliation cycles (the common case once detected). Documented
   in code.

---

## Deferred Items / Same-Sprint Follow-Ons

- **Session 2c.2** — auto-clear (5 consecutive zero-shares cycles)
  using `_remove_gated_symbol_from_db()` already in place.
- **Session 2d** — operator override REST endpoint
  `POST /api/v1/reconciliation/phantom-short-gate/clear` calling
  `_remove_gated_symbol_from_db()`.
- **DEF-177 (open)** — when Sprint 31.93 (or the cross-domain RejectionStage
  session) lands, `phantom_short_gate` should become a distinct
  `RejectionStage` enum value rather than overloading
  `"risk_manager"`. Captured in the existing DEF-177 scope.

---

## Test Output

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q
...
5159 passed, 36 warnings in 55.13s
```

```
$ python -m pytest tests/execution/order_manager/test_session2c1_phantom_short_gate.py -v
test_phantom_short_gate_engages_on_broker_orphan_short PASSED
test_gate_blocks_order_approved_for_gated_symbol PASSED
test_gate_does_not_block_other_symbols PASSED
test_phantom_short_gated_symbols_persist_to_sqlite PASSED
test_gate_state_rehydrated_on_restart_before_event_processing PASSED
test_gate_state_survives_argus_restart_blocks_entries PASSED
6 passed
```

---

## Self-Assessment: CLEAN

Every spec requirement is addressed; the only deviations are the two
flagged judgment calls (stub `_remove_gated_symbol_from_db` ahead of
need; tracking-set for fire-and-forget tasks). Both are additive to
the spec and documented. No behavior outside the spec scope. M5
ordering verified in tests. Do-not-modify regions zero-diff (with
the scoped main.py exception per invariant 15).

---

*End Sprint 31.91 Session 2c.1 close-out report.*
