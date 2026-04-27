# Sprint 31.91, Session 2c.1: Per-Symbol Gate State + Handler + SQLite Persistence (M5 Rehydration Ordering)

> **Track:** Side-Aware Reconciliation Contract (Sessions 2a → 2b.1 → 2b.2 → **2c.1** → 2c.2 → 2d).
> **Position in track:** Fourth session. Adds the per-symbol entry gate that engages when 2b.1 detects a phantom short. SQLite-backed for restart safety.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038, RULE-050, RULE-019, RULE-007 all apply.

2. Read these files to load context:
   - `argus/execution/order_manager.py` — find the `OrderApprovedEvent` handler (`grep -n "OrderApprovedEvent\|on_order_approved\|on_approved" argus/execution/order_manager.py`)
   - `argus/main.py` — startup sequence; find where reconciliation hooks attach and where Event Bus subscribers are registered (this is the M5 rehydration-ordering pin point)
   - `data/operations.db` schema (or sibling SQLite manager pattern in the codebase — `grep -rn "operations.db\|aiosqlite" argus/`)
   - `argus/core/events.py` — `OrderApprovedEvent` definition
   - Session 2b.1's `_broker_orphan_long_cycles` and the `_handle_broker_orphan_short` handler (Session 2c.1's gate engagement happens inside this handler)
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D5 acceptance criteria (Session 2c.1 portion)

3. Run the scoped test baseline:

   ```
   python -m pytest tests/execution/ -n auto -q
   ```

4. Verify you are on the correct branch: **`main`**.

5. Verify Sessions 2a + 2b.1 + 2b.2 deliverables are present on `main`:

   ```bash
   grep -n "ReconciliationPosition\|_broker_orphan_long_cycles" argus/execution/order_manager.py
   grep -n "phantom_short" argus/execution/order_manager.py | head -5
   grep -n "long_positions = \[p for p in" argus/core/risk_manager.py argus/core/health.py
   ```

6. **Pre-flight grep — locate startup-sequence rehydration insertion point in `main.py`:**

   The M5 invariant requires gate-state rehydration BEFORE Event Bus subscription begins processing `OrderApprovedEvent`. Find the exact line where:

   ```bash
   grep -n "subscribe\|event_bus.register\|OrderApprovedEvent" argus/main.py | head -20
   ```

   The rehydration code must be inserted BEFORE the line where the OrderManager subscribes to `OrderApprovedEvent` (or where the event bus starts publishing). Typically this is during Phase 9.x of startup; verify by reading the surrounding context.

7. **Pre-flight grep — verify `data/operations.db` SQLite usage pattern:**

   ```bash
   grep -rn "operations.db\|operations\.db" argus/ | head -10
   grep -rn "import aiosqlite" argus/ | head -10
   ```

   If `data/operations.db` does not yet exist, Session 2c.1 creates it. If it exists with other tables, Session 2c.1 adds the `phantom_short_gated_symbols` table. Reviewer in Tier 2 will confirm the integration approach matches whatever pattern is already in use.

## Objective

Add per-symbol entry-gating: when `phantom_short` alert fires for a symbol (Session 2b.1's `_handle_broker_orphan_short`), the symbol enters `_phantom_short_gated_symbols`, and the `OrderApprovedEvent` handler rejects subsequent entries on that symbol. Per-symbol granularity: gating AAPL does not affect MSFT.

The state must be SQLite-persisted to `data/operations.db`'s `phantom_short_gated_symbols` table, and rehydrated on startup BEFORE the OrderManager begins processing `OrderApprovedEvent` (M5 disposition). This closes the ~60s window of unsafe entries on restart that would otherwise exist.

Auto-clear logic (5 consecutive zero-shares cycles) is deferred to Session 2c.2; Session 2c.1 only implements engagement and persistence.

## Requirements

1. **Add `_phantom_short_gated_symbols: set[str]` state field** to `OrderManager.__init__()`:

   ```python
   # Sprint 31.91 Session 2c.1: per-symbol entry gate. Symbols in this set
   # are blocked at the OrderApprovedEvent handler. Engagement: Session
   # 2b.1's _handle_broker_orphan_short adds; auto-clear (5-cycle) lands
   # in Session 2c.2; operator override lands in Session 2d.
   # SQLite-persisted to data/operations.db (M5 rehydration ordering).
   self._phantom_short_gated_symbols: set[str] = set()
   ```

2. **Engage the gate inside Session 2b.1's `_handle_broker_orphan_short`:**

   The handler already emits the alert. Add (after the alert emission):

   ```python
   def _handle_broker_orphan_short(
       self, symbol: str, recon_pos: "ReconciliationPosition"
   ) -> None:
       """Sprint 31.91 Session 2b.1 + 2c.1."""
       if not self._config.reconciliation.broker_orphan_alert_enabled:
           return

       # ... existing log + alert emission from 2b.1 ...

       # NEW (Session 2c.1): engage per-symbol entry gate
       if (
           self._config.reconciliation.broker_orphan_entry_gate_enabled
           and symbol not in self._phantom_short_gated_symbols
       ):
           self._phantom_short_gated_symbols.add(symbol)
           # Persist immediately (per-engagement write; the table is small
           # and writes are infrequent — phantom shorts should be rare).
           asyncio.create_task(self._persist_gated_symbol(symbol, "engaged"))
           self._logger.critical(
               "Phantom-short gate ENGAGED for %s. Future OrderApprovedEvents "
               "for this symbol will be rejected until gate clears (5 "
               "consecutive zero-shares cycles per Session 2c.2 OR operator "
               "override per Session 2d).",
               symbol,
           )
   ```

   Notes:
   - The `asyncio.create_task` for persistence is fire-and-forget — the persistence is best-effort during the same reconciliation cycle. If ARGUS crashes before the write completes, rehydration on restart will miss this symbol. The acceptable mitigation is that the next reconciliation cycle (~1 minute later) re-detects the phantom short and re-engages the gate. This trade-off is intentional; making persistence synchronous would block reconciliation.
   - The check `symbol not in self._phantom_short_gated_symbols` makes the engagement idempotent — re-detection of a still-active phantom short does not produce duplicate persistence writes.

3. **Gate the `OrderApprovedEvent` handler:**

   Locate the existing `OrderApprovedEvent` handler in OrderManager. Add at the top of the handler:

   ```python
   async def on_order_approved(self, event: OrderApprovedEvent) -> None:
       # Sprint 31.91 Session 2c.1: per-symbol phantom-short entry gate.
       symbol = event.symbol  # or however the symbol is extracted in the existing handler
       if symbol in self._phantom_short_gated_symbols:
           self._logger.critical(
               "OrderApprovedEvent REJECTED for %s: symbol is in "
               "phantom_short_gated_symbols. Operator must clear via "
               "POST /api/v1/reconciliation/phantom-short-gate/clear "
               "(Session 2d) or wait for 5-cycle auto-clear (Session 2c.2).",
               symbol,
           )
           # Emit OrderRejectedEvent (or whatever the existing rejection
           # pattern uses; mirror DEC-367 margin-circuit rejection shape)
           rejected = OrderRejectedEvent(
               # ... fill from `event` ...
               reason="phantom_short_gate",
               reason_detail=f"Symbol {symbol} is gated due to phantom-short detection.",
           )
           self._event_bus.publish(rejected)
           return  # do NOT process further

       # ... existing handler body unchanged ...
   ```

   Notes:
   - The reason code `phantom_short_gate` MUST be a new, distinct rejection code — do not overload `concurrent_positions_exceeded` or any existing code.
   - The rejection logic is at the TOP of the handler (before any existing logic), so the gate is the FIRST check. This mirrors how DEC-367 margin-circuit rejection happens early.

4. **SQLite persistence — `phantom_short_gated_symbols` table:**

   Create the table in `data/operations.db`. The schema:

   ```sql
   CREATE TABLE IF NOT EXISTS phantom_short_gated_symbols (
       symbol TEXT PRIMARY KEY,
       engaged_at_utc TEXT NOT NULL,
       engaged_at_et TEXT NOT NULL,
       engagement_source TEXT NOT NULL,  -- "engaged" or "operator_re-engaged"
       last_observed_short_shares INTEGER  -- nullable; updated on re-detection
   );
   ```

   Methods on OrderManager (or a delegated `OperationsStore` if one exists; verify):

   ```python
   async def _persist_gated_symbol(self, symbol: str, source: str) -> None:
       """Write/upsert a gated-symbol entry to operations.db."""
       async with aiosqlite.connect(self._operations_db_path) as db:
           await db.execute(
               """
               INSERT OR REPLACE INTO phantom_short_gated_symbols
               (symbol, engaged_at_utc, engaged_at_et, engagement_source)
               VALUES (?, ?, ?, ?)
               """,
               (symbol, utcnow_iso(), etnow_iso(), source),
           )
           await db.commit()

   async def _remove_gated_symbol_from_db(self, symbol: str) -> None:
       """Delete a gated-symbol entry from operations.db. Called by
       Session 2c.2 (auto-clear) and Session 2d (operator override).
       Stub for 2c.1 — implementation lands in 2c.2."""
       async with aiosqlite.connect(self._operations_db_path) as db:
           await db.execute(
               "DELETE FROM phantom_short_gated_symbols WHERE symbol = ?",
               (symbol,),
           )
           await db.commit()

   async def _rehydrate_gated_symbols_from_db(self) -> None:
       """M5 rehydration: load gated symbols from operations.db into
       in-memory state. Called from main.py BEFORE OrderApprovedEvent
       subscription begins."""
       async with aiosqlite.connect(self._operations_db_path) as db:
           async with db.execute(
               "SELECT symbol FROM phantom_short_gated_symbols"
           ) as cursor:
               rows = await cursor.fetchall()
       for (symbol,) in rows:
           self._phantom_short_gated_symbols.add(symbol)
       if self._phantom_short_gated_symbols:
           self._logger.critical(
               "Phantom-short gate REHYDRATED on startup. Gated symbols: %s. "
               "Operator must investigate (Sprint 31.91 runbook).",
               sorted(self._phantom_short_gated_symbols),
           )
   ```

   Notes:
   - If the project uses a connection-pooling pattern (a single shared aiosqlite connection lifecycle), match it instead of opening a new connection per write. Verify by grepping for existing aiosqlite patterns; per RULE-007, do not introduce a new pattern.
   - The `_operations_db_path` field is added to OrderManager.__init__() — load from config (`config.persistence.operations_db_path: "data/operations.db"` if such a config exists; otherwise hard-code with a config TODO).

5. **M5 rehydration ordering in `argus/main.py`:**

   This is the safety-critical piece. The rehydration MUST happen BEFORE the OrderManager subscribes to `OrderApprovedEvent`. Pre-flight identified the subscription line. Insert immediately before:

   ```python
   # Sprint 31.91 Session 2c.1: M5 — rehydrate phantom-short gate state
   # BEFORE OrderApprovedEvent subscription. Without this ordering, ~60s
   # of unsafe entries on restart could land before reconciliation
   # re-detects the phantom shorts and re-engages the gate.
   await order_manager._rehydrate_gated_symbols_from_db()

   # ...existing OrderApprovedEvent subscription line...
   event_bus.subscribe(OrderApprovedEvent, order_manager.on_order_approved)
   ```

   Notes:
   - The exact subscription line will vary based on the project's pattern. Per pre-flight, locate it and pin the rehydration immediately before.
   - This counts as a scoped exception to invariant 15's "main.py startup invariant region" rule — Session 2c.1's rehydration code is permitted per the invariant 15 explicit exception ("Session 2c.1's startup gate-state rehydration code"). Verify the diff is confined to this block; do not touch anything else in `main.py`.

6. **Add config field `broker_orphan_entry_gate_enabled: bool = True`** to `ReconciliationConfig`:

   ```python
   broker_orphan_entry_gate_enabled: bool = Field(
       default=True,
       description=(
           "When True, broker-orphan SHORT detection engages the per-symbol "
           "entry gate (rejecting OrderApprovedEvents for the gated symbol). "
           "When False, the alert still fires but no entries are blocked — "
           "operator-only mitigation mode."
       ),
   )
   ```

   Update YAMLs.

7. **DEC-367 margin-circuit independence.** The phantom-short gate state is independent of the margin-circuit state. A symbol can be in BOTH `_phantom_short_gated_symbols` AND the margin-circuit set; both rejections fire (most-restrictive wins, but operationally either rejection blocks the order). Verify by inspection.

8. **Per-symbol granularity.** Gating AAPL does NOT affect MSFT. The data structure is a `set[str]`, so granularity is by construction. Verify with Test 3.

9. **No edits to do-not-modify regions.** Specifically:
   - `argus/execution/order_manager.py:1670-1750`
   - `argus/main.py` startup invariant region — Session 2c.1 has a SCOPED exception for the rehydration insertion (per invariant 15's "Session 2c.1's startup gate-state rehydration code")
   - `argus/models/trading.py`, `argus/execution/alpaca_broker.py`, `argus/data/alpaca_data_service.py`, `argus/execution/ibkr_broker.py`, `argus/execution/broker.py`
   - `argus/core/risk_manager.py`, `argus/core/health.py`
   - `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`, `workflow/`

## Tests (~6 new pytest)

1. **`test_phantom_short_gate_engages_on_broker_orphan_short`**
   - Setup: `_managed_positions` empty for AAPL; broker-orphan short detected.
   - Trigger reconciliation.
   - Assert: `AAPL` in `_phantom_short_gated_symbols`; SQLite write occurred (`SELECT * FROM phantom_short_gated_symbols WHERE symbol='AAPL'` returns one row).
   - Assert: idempotent — re-triggering reconciliation does NOT add a duplicate row (INSERT OR REPLACE).

2. **`test_gate_blocks_order_approved_for_gated_symbol`**
   - Setup: `_phantom_short_gated_symbols = {"AAPL"}`.
   - Publish an `OrderApprovedEvent` for AAPL.
   - Assert: `OrderRejectedEvent` with `reason="phantom_short_gate"` published; downstream order placement does NOT fire.

3. **`test_gate_does_not_block_other_symbols`** (per-symbol granularity)
   - Setup: `_phantom_short_gated_symbols = {"AAPL"}`.
   - Publish an `OrderApprovedEvent` for MSFT (different symbol).
   - Assert: handler proceeds normally; MSFT order is placed.

4. **`test_phantom_short_gated_symbols_persist_to_sqlite`**
   - Setup: trigger gate engagement for AAPL via reconciliation.
   - Assert: `data/operations.db` contains the row immediately after engagement (read with a fresh connection).
   - Assert: row schema fields populated (engaged_at_utc, engaged_at_et, engagement_source="engaged").

5. **`test_gate_state_rehydrated_on_restart_before_event_processing`** (M5 invariant)
   - Setup: pre-populate `data/operations.db` with `{symbol: "AAPL"}` (simulating prior session). Construct a fresh OrderManager and main.py-style startup sequence.
   - Trigger startup: `_rehydrate_gated_symbols_from_db()` runs FIRST.
   - Then subscribe to `OrderApprovedEvent`.
   - Publish an `OrderApprovedEvent` for AAPL.
   - Assert: `_phantom_short_gated_symbols == {"AAPL"}` BEFORE the subscription happened.
   - Assert: the `OrderApprovedEvent` is rejected (the gate is in place from the moment subscription begins).
   - **Critical anti-regression:** if rehydration runs AFTER subscription, this test must FAIL — verify by reordering in a pytest experiment (do not commit the experiment).

6. **`test_gate_state_survives_argus_restart_blocks_entries`** (E2E)
   - Setup: trigger gate engagement; run a "shutdown" (close DB connections); reconstruct the OrderManager + startup sequence.
   - Assert: gate state is rehydrated; subsequent `OrderApprovedEvent` for AAPL is rejected.
   - End-to-end coverage of the persistence + rehydration flow.

## Definition of Done

- [ ] `_phantom_short_gated_symbols` state field initialized.
- [ ] Gate engagement in `_handle_broker_orphan_short` (Session 2b.1 handler extended); idempotent.
- [ ] `on_order_approved` handler rejects gated symbols with `reason="phantom_short_gate"`.
- [ ] Per-symbol granularity verified.
- [ ] `phantom_short_gated_symbols` SQLite table created in `data/operations.db`.
- [ ] M5 rehydration ordering: `_rehydrate_gated_symbols_from_db()` runs BEFORE OrderApprovedEvent subscription in main.py startup.
- [ ] `broker_orphan_entry_gate_enabled: bool = True` config field added.
- [ ] DEC-367 margin-circuit state independence verified.
- [ ] 6 new tests; all passing.
- [ ] CI green; pytest baseline ≥ 5,134.
- [ ] All do-not-modify list items show zero `git diff` (with the scoped exception for `main.py` rehydration insertion).
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-2c.1-closeout.md`.

## Close-Out Report

Standard structure. Verdict JSON:

```json
{
  "session": "2c.1",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 6,
  "tests_total_after": <fill>,
  "files_modified": [
    "argus/execution/order_manager.py",
    "argus/main.py",
    "argus/core/config.py",
    "<test files>"
  ],
  "donotmodify_violations": 0,
  "main_py_scoped_exception": "M5 rehydration insertion before OrderApprovedEvent subscription",
  "tier_3_track": "side-aware-reconciliation"
}
```

Cite in close-out:
- The exact `main.py` line range of the rehydration insertion.
- Whether `data/operations.db` was created or extended in this session.
- The aiosqlite usage pattern matched (per-write connection vs connection-pooled).

## Tier 2 Review Invocation

Standard pattern. Backend safety reviewer template. Review report at `session-2c.1-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Rehydration ordering on startup (M5).** This is the central reviewer focus. Read `main.py` diff and verify the rehydration call appears textually BEFORE the `OrderApprovedEvent` subscription. Run Test 5 explicitly. The 60s safety window is the bound on missed protection on restart.

2. **SQLite transactions atomic.** The INSERT OR REPLACE is atomic by SQLite default. Reviewer confirms the `await db.commit()` runs on the success path; a crash mid-write loses the new row but does not corrupt existing rows.

3. **Per-symbol granularity holds.** Test 3 verifies. Reviewer additionally inspects the `_phantom_short_gated_symbols` data structure (must be `set[str]`) and the gate check (`if symbol in ...`), which is O(1) and per-symbol.

4. **`asyncio.create_task` fire-and-forget.** The persistence write is fire-and-forget. Reviewer confirms:
   - The task is not awaited (intentional non-blocking).
   - Failure of the persistence write does not crash reconciliation (the task's exception is captured in the task object; an unobserved task exception only affects future cycles).
   - The task is created from within an asyncio context (otherwise `asyncio.create_task` raises).

5. **Idempotency.** Re-detection on the same symbol does not produce duplicate alerts or duplicate persistence writes. The `if symbol not in self._phantom_short_gated_symbols` guard is the structural enforcement; reviewer verifies.

6. **DEC-367 margin-circuit independence.** Reviewer reads the existing margin-circuit logic and confirms it has no awareness of `_phantom_short_gated_symbols`. The two are independent. A symbol in both is rejected by both gates (the first to hit the order in handler ordering wins, but operationally either rejection blocks the order).

7. **Configuration gate (`broker_orphan_entry_gate_enabled`).** When False, the alert still fires (Session 2b.1's behavior) but no entries are blocked. Reviewer verifies by scanning the gate-engagement and gate-check code paths.

8. **No regressions from Session 2b.1.** The gate engagement in `_handle_broker_orphan_short` is additive — the alert emission still happens regardless of gate state. Reviewer runs Session 2b.1's tests and confirms they still pass.

## Sprint-Level Regression Checklist (for @reviewer)

- **Invariant 5:** PASS — expected ≥ 5,134.
- **Invariant 9 (IMPROMPTU-04 startup invariant unchanged):** PASS — Session 2c.1's `main.py` edit is the rehydration insertion; the IMPROMPTU-04 fix is at a different location. Reviewer reads the diff to confirm separation.
- **Invariant 10 (DEC-367 margin circuit unchanged):** PASS — gate is independent of margin circuit.
- **Invariant 14:** Row "After Session 2c.1" — Recon detects shorts = "full (alert + gate + persistence)".
- **Invariant 15:** PASS with scoped exception (Session 2c.1 main.py rehydration insertion documented in invariant 15).

## Sprint-Level Escalation Criteria (for @reviewer)

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **A4** (gate-state rehydration interacts with reconnect-recovery in a way the M5 test didn't model — premature rehydration before broker connection is established could leave gate state stale).
- **B1, B3, B4, B6** — standard halt conditions.
- **C5** (`main.py` edit scope) — most likely escalation site this session; the rehydration insertion is the only permitted edit.
- **C7** (existing tests using OrderApprovedEvent fail because the gate-check is now ALWAYS the first check; pre-existing tests may not have a gate-empty fixture).

---

*End Sprint 31.91 Session 2c.1 implementation prompt.*
