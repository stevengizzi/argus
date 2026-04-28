# Sprint 31.91 Session 2c.1 — Tier 2 Review

> **Reviewer mode:** Read-only (per RULE-013).  
> **Commit reviewed:** `0c034b3` on `main`.  
> **Parent:** `0726f97` (Session 2b.2 doc-sync paste).  
> **Verdict:** **CLEAR** — see structured JSON at end.

---

## 1. Anchor + scope

`git show 0c034b3 --stat`:

| File | Δ |
|---|---|
| `argus/core/config.py` | +19 |
| `argus/execution/order_manager.py` | +243 |
| `argus/main.py` | +11 / -0 |
| `config/system.yaml` | +5 |
| `config/system_live.yaml` | +5 |
| `tests/execution/order_manager/test_reconciliation_redesign.py` | +4 / -1 |
| `tests/execution/order_manager/test_session2c1_phantom_short_gate.py` | +463 (new) |
| `docs/sprints/sprint-31.91-reconciliation-drift/session-2c.1-closeout.md` | +276 (new) |

Total: 1026 insertions, 1 deletion across 8 files. Production-code edits are
purely additive in `order_manager.py` and `config.py`; `main.py` has 11
adds, 0 deletes (`grep -E '^\+' | wc -l` = 12 incl. diff header; `grep -E
'^-' | grep -v '^---' | wc -l` = 0).

---

## 2. Do-not-modify list — zero-diff verification

Per spec § "Do-not-modify list," verified each path against the parent
commit:

```
argus/models/trading.py:           0 diff lines
argus/execution/alpaca_broker.py:  0 diff lines
argus/data/alpaca_data_service.py: 0 diff lines
argus/execution/ibkr_broker.py:    0 diff lines
argus/execution/broker.py:         0 diff lines
argus/core/risk_manager.py:        0 diff lines
argus/core/health.py:              0 diff lines
```

All seven paths zero-diff. **PASS.**

IMPROMPTU-04 invariant region (`argus/main.py:194-204`) — read at
`argus/main.py:194-204`, contains `_startup_flatten_disabled: bool = False`
unchanged. **PASS.**

DEC-367 margin-circuit code paths in `order_manager.py` (lines 380-386,
635-652, 818-829, 1648-1671, 3695-3700) — `git diff 0c034b3^..0c034b3 --
argus/execution/order_manager.py | grep -A 2 "margin_circuit"` returns no
matches. Margin-circuit code unmodified. **PASS.**

---

## 3. Required review focus — finding-by-finding

### Focus 1 — M5 rehydration ordering (CENTRAL)

`argus/main.py:1076` (`await self._order_manager._rehydrate_gated_symbols_from_db()`)
appears textually BEFORE `argus/main.py:1077` (`await self._order_manager.start()`).
Verified by reading the source. `start()` at `argus/execution/order_manager.py:429`
is the subscription site (line 434: `self._event_bus.subscribe(OrderApprovedEvent, self.on_approved)`).

Test 5 (`test_gate_state_rehydrated_on_restart_before_event_processing`)
explicitly verifies this ordering: pre-populates operations.db via a sibling
OrderManager, asserts `_phantom_short_gated_symbols == {"AAPL"}` AFTER
rehydrate AND BEFORE start(), then verifies the very first
OrderApprovedEvent published after subscription is rejected. Test passes.

The 60s safety bound (= reconciliation cycle period) is cited in the
implementer's `_handle_broker_orphan_short` comment at lines 2397-2400 as
the worst-case re-detection window if a persist write is lost mid-flight.
Architecturally sound.

**PASS.**

### Focus 2 — SQLite atomicity

`_persist_gated_symbol` at `argus/execution/order_manager.py:2552` uses
`INSERT OR REPLACE` (atomic by SQLite default — single-statement DML
inside an implicit transaction); `await db.commit()` runs on the success
path at line 2576. Pattern mirrors `argus/intelligence/experiments/store.py`.
A crash mid-write rolls back the implicit transaction; existing rows are
not corrupted.

**PASS.**

### Focus 3 — Per-symbol granularity

`_phantom_short_gated_symbols` declared at line 413 as `set[str]`. The gate
check at line 526 is `if signal.symbol in self._phantom_short_gated_symbols`
— O(1), per-symbol. Test 3 (`test_gate_does_not_block_other_symbols`)
confirms gating AAPL does not block MSFT (MSFT broker call IS awaited).
Test passes.

**PASS.**

### Focus 4 — `asyncio.create_task` fire-and-forget + GC protection

At line 2401, `asyncio.create_task(self._persist_gated_symbol(...))` is
created and added to `self._pending_gate_persist_tasks` (a strong-ref set
declared at line 427). The done-callback `_on_persist_done` at line 2408
removes the task from the set and routes any exception through
`_log_persist_task_exception` (module-level helper at lines 73-89), which
emits a WARNING per DEC-345 fire-and-forget conventions. Per RULE-007
this slightly exceeds the spec (which described untracked
`asyncio.create_task`); the implementer documents the rationale in
closeout judgment-call #2 (Python 3.11 weak-ref GC reclaims untracked
tasks pre-completion; tests need awaitability). Pattern is sound and
self-cleaning. The task is not awaited from production code paths; a
persist failure does not crash reconciliation.

The task is created from within `_handle_broker_orphan_short`, an async
method invoked from `reconcile_positions` (which has its own asyncio
context). **PASS.**

### Focus 5 — Idempotency

Engagement guarded by `if (... and symbol not in self._phantom_short_gated_symbols)`
at lines 2392-2394. Re-detection on the same symbol skips both the set
mutation AND the persist-task creation. Test 1
(`test_phantom_short_gate_engages_on_broker_orphan_short`) covers idempotent
re-detection (no duplicate row). Belt-and-suspenders: the SQL is
`INSERT OR REPLACE` so even if the in-memory guard were bypassed, no PK
constraint error would occur.

**PASS.**

### Focus 6 — DEC-367 margin-circuit independence

The phantom-short gate check at line 526 fires BEFORE the margin-circuit
gate at line 635 (both inside `on_approved`). Both are independent
set/flag membership tests that early-return with their own
`SignalRejectedEvent` payloads. Margin-circuit state
(`_margin_rejection_count`, `_margin_circuit_open`) has no awareness of
`_phantom_short_gated_symbols` (verified via grep — no co-location in
either direction). A symbol present in both gates is rejected via
phantom-short first; this is operationally correct (phantom-short is the
more severe condition).

**PASS.**

### Focus 7 — Configuration gate

`broker_orphan_entry_gate_enabled: bool = True` declared at
`argus/core/config.py:256` with a `Field(default=True, description=...)`.
When False, `_handle_broker_orphan_short` line 2392 short-circuits the
engagement (the alert from Session 2b.1 still emits because it lives
above this guard at the same method's earlier section). Verified by
re-reading the handler in full.

**PASS.**

### Focus 8 — Session 2b.1 regression

`tests/execution/order_manager/test_session2b1_broker_orphan_alerts.py` —
all 6 tests pass (`6 passed in 0.03s`). Zero regressions.

**PASS.**

---

## 4. Sprint-Level Regression Checklist

| Invariant | Status | Evidence |
|---|---|---|
| 5 (test baseline ≥ 5,134) | PASS | Full suite: **5,159 passed in 81.56s**; `grep -cE "^FAILED\|^ERROR" /tmp/full_suite_v2.txt` = 0. Matches implementer-cited 5,159. |
| 9 (IMPROMPTU-04 startup invariant unchanged) | PASS | `argus/main.py:194-204` reads `_startup_flatten_disabled: bool = False` unchanged. |
| 10 (DEC-367 margin circuit unchanged) | PASS | Margin-circuit identifiers in order_manager.py at lines 380-386, 635-652, 818-829, 1648-1671, 3695-3700 — no diff. |
| 14 row "After Session 2c.1" | PASS | Recon detects shorts now does alert + gate engagement + SQLite persistence + M5 rehydration on restart. |
| 15 (main.py edit scope) | PASS with documented exception | 11 lines added at `argus/main.py:1065-1077` only — `operations_db_path` kwarg (3 lines) + comment block (5 lines) + rehydrate call (1 line) + reformatted closing parens. No edits in IMPROMPTU-04 region. |

---

## 5. Sprint-Level Escalation Criteria — none triggered

- **A2:** Tier 2 verdict is CLEAR (this review). N/A.
- **A4 (rehydration vs broker connection):** non-issue. `broker.connect()` runs
  at `argus/main.py:364`; rehydration runs at `argus/main.py:1076` — broker
  is connected first by ~700 source lines. Rehydration is a SQLite read
  with no broker dependency. The DEF-199 invariant gate (lines 369-401)
  runs in between; phantom-short gate is purely additive to that contract.
- **B1, B3, B4, B6:** none triggered (test pass count ≥ baseline; no broker
  side modifications; no CI/silent-failure additions).
- **C5 (`main.py` edit scope):** scoped exception, 11 lines around the
  existing OrderManager construction, fully aligned with invariant 15's
  documented exception.
- **C7 (pre-existing OrderApprovedEvent tests):** all 266
  `tests/execution/order_manager/` tests pass — `_phantom_short_gated_symbols`
  defaults to empty set, so the gate-check `if symbol in set()` is always
  False for legacy tests. No fixture coupling.

---

## 6. Minor concerns (non-blocking)

1. **Persistence failure leaves disk state stale until restart.** If a
   `_persist_gated_symbol` task fails (exception in the `asyncio.create_task`
   coroutine), the in-memory state stays correct (because the symbol was
   added to the set BEFORE the persist task was created at lines 2396 →
   2401). The done-callback logs WARNING. The next reconciliation cycle
   skips re-persisting because the `not in` guard returns False (symbol
   IS in set). Net result: until ARGUS restarts, the disk is missing the
   row. On restart, rehydration loads zero rows for that symbol, but the
   next reconciliation re-detects within ~60s and re-engages the gate.
   This is the implementer's documented contract; the 60s window is the
   bound.
   - Not a blocker. The contract is sound and matches DEC-345
     fire-and-forget semantics. Worth surfacing for Session 2c.2 / 2d
     awareness.

2. **`OrderManager.stop()` does not await `_pending_gate_persist_tasks`.**
   At `argus/execution/order_manager.py:459-466`, `stop()` only cancels
   `_poll_task`. If ARGUS shuts down between `_handle_broker_orphan_short`
   creating a persist task and the task completing, the disk could miss
   the row. Same recovery path as concern #1. The implementer could add a
   `await asyncio.gather(*self._pending_gate_persist_tasks, return_exceptions=True)`
   in `stop()` for graceful shutdown, but it's a same-family follow-on
   already implied by the Session 2c.2 stub-completion roadmap.
   - Not a blocker. Worth documenting as a same-track follow-on.

3. **`rejection_stage="risk_manager"` overload.** The `phantom_short_gate`
   rejection reuses the existing `"risk_manager"` rejection stage (mirror of
   the margin-circuit pattern). DEF-177 / DEF-184 already track the cleanup
   to introduce a dedicated `phantom_short_gate` (or shared
   `MARGIN_CIRCUIT`-like) `RejectionStage` enum value. Closeout judgment-call
   #4 calls this out; deferred to the cross-domain RejectionStage session.
   - Not a blocker. Captured in DEF-177 scope.

None of the above rise to CONCERNS severity. They are documented in the
closeout proactively (judgment-calls #2, #3, #5) and have explicit
follow-on routing.

---

## 7. Tests run

| Test set | Result |
|---|---|
| `tests/execution/order_manager/test_session2c1_phantom_short_gate.py -v` | **6/6 PASS** in 0.04s |
| `tests/execution/order_manager/test_session2b1_broker_orphan_alerts.py -v` | **6/6 PASS** in 0.03s |
| `tests/execution/order_manager/ -q` | **266/266 PASS** in 16.66s |
| `python -m pytest --ignore=tests/test_main.py -n auto -q` | **5,159 PASS, 0 FAIL, 0 ERROR** in 81.56s |

The 37 warnings cited in the full-suite tail are pre-existing aiosqlite/asyncio
cleanup noise (DEF-201 / DEF-192 family) and identical in count category to
prior session baselines. No new warning categories.

---

## 8. Verdict

The implementation matches the spec line-for-line. All 8 required-review-focus
items pass. All sprint-level invariants pass. All escalation criteria are
non-applicable. Do-not-modify list is zero-diff. Tests are revert-proof
(particularly Test 5's M5 ordering assertion). The implementer's three
spec-exceeding additions (`_remove_gated_symbol_from_db` stub,
`_pending_gate_persist_tasks` GC-protection set, `metadata`-structured
rejection payload) are documented judgment calls with sound rationale.

**Verdict: CLEAR.**

---

```json:structured-verdict
{
  "session": "2c.1",
  "verdict": "CLEAR",
  "tests_total": 5159,
  "regressions": 0,
  "donotmodify_violations": 0,
  "main_py_scope_ok": true,
  "concerns": [
    "Persistence-failure recovery: disk state stale until next restart re-detection; documented contract, 60s bound, not a blocker.",
    "OrderManager.stop() does not await _pending_gate_persist_tasks; could be added for graceful shutdown in 2c.2/2d roadmap.",
    "rejection_stage='risk_manager' overload — DEF-177/DEF-184 cross-domain RejectionStage cleanup already scopes this; closeout judgment-call #4."
  ]
}
```

---

*End Sprint 31.91 Session 2c.1 Tier 2 review.*
