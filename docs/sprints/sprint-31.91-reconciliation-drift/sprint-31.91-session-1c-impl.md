# Sprint 31.91, Session 1c: Broker-Only Paths Safety + Reconstruct Docstring

> **🔻 GATE SESSION FOR TIER 3 ARCHITECTURAL REVIEW #1 🔻**
>
> Session 1c is the final session of the OCA architecture track. After
> this session lands cleanly on `main` (Tier 2 CLEAR + green CI), Tier 3
> architectural review #1 fires per `escalation-criteria.md` §A1 and
> `session-breakdown.md` §"TIER 3 ARCHITECTURAL REVIEW #1 FIRES HERE".
>
> Tier 3 scope: combined diff of **Sessions 0 + 1a + 1b + 1c** on `main`
> (per third-pass LOW #17 — Session 0's API contract is part of the OCA
> architecture and Session 1c consumes its `await_propagation=True`
> semantics). This means Session 1c's close-out must be Tier-3-ready: the
> implementer should anticipate the architectural questions and answer
> them in the close-out where possible.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038 (grep-verify discipline), RULE-050 (CI green), RULE-007 (out-of-scope discoveries), and RULE-019 (test-count must not decrease) all apply.

2. Read these files to load context:
   - `argus/execution/order_manager.py:1920` — `_flatten_unknown_position` (verify line; may have drifted by ±5 per RULE-038)
   - `argus/execution/order_manager.py:2021` — `_drain_startup_flatten_queue` (verify)
   - `argus/execution/order_manager.py:1813` — `reconstruct_from_broker` (verify)
   - `argus/execution/order_manager.py:1705-1755` — EOD Pass 2 loop (read-only; do not modify; this is the caller of `_flatten_unknown_position` and the reason cancel-timeout failure-mode docs matter)
   - `argus/execution/broker.py` — confirm Session 0's `cancel_all_orders(symbol, await_propagation)` ABC signature and `CancelPropagationTimeout` exception class are present
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D4 acceptance criteria
   - `docs/sprints/sprint-31.91-reconciliation-drift/spec-by-contradiction.md` — Do NOT modify list
   - `docs/sprints/sprint-31.91-reconciliation-drift/PHASE-D-OPEN-ITEMS.md` — Item 2 (cancel-timeout failure-mode)

3. Run the test baseline (DEC-328 — Session 4+ of sprint, scoped is fine; full will run at sprint-close gate):

   ```
   python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q
   ```

   Expected: all passing (Session 1b's close-out confirmed scoped; full suite confirmed by Session 0's close-out).

4. Verify you are on the correct branch: **`main`**.

5. Verify Sessions 0 + 1a + 1b deliverables are present on `main`:

   ```bash
   grep -n "def cancel_all_orders" argus/execution/broker.py
   grep -n "class CancelPropagationTimeout" argus/execution/broker.py
   grep -n "_is_oca_already_filled_error" argus/execution/order_manager.py
   grep -n "test_no_sell_without_oca_when_managed_position_has_oca" tests/_regression_guards/
   ```

   All four must match. If any are missing, halt — Sessions 0/1a/1b have not all landed.

6. **Pre-flight grep — verify exactly 3 broker-only SELL paths exist that are NOT covered by Session 1b's grep regression guard:**

   The Session 1b regression guard `test_no_sell_without_oca_when_managed_position_has_oca` permits `# OCA-EXEMPT: <reason>` comments at exempt sites. Session 1c is exactly where those exemption markers are added — at the broker-only paths where no `ManagedPosition` exists.

   ```bash
   grep -n "# OCA-EXEMPT:" argus/execution/order_manager.py
   ```

   Initially this should return zero results. Session 1c will add 3 such markers (one per broker-only path). If you find more than 0 at pre-flight, halt and reconcile against the spec.

   Also grep for the SELL placements you'll be modifying:

   ```bash
   grep -n -A 2 "_broker.place_order" argus/execution/order_manager.py | grep -B 1 "SELL\|side=OrderSide.SELL"
   ```

   Cross-reference each match against this prompt's 3 functions. Any SELL placement found inside `_flatten_unknown_position`, `_drain_startup_flatten_queue`, or `reconstruct_from_broker` is in scope. If you find SELL placements in OTHER broker-only functions not listed here, halt and escalate — the spec needs amendment.

## Objective

Make all 3 broker-only SELL paths safe by clearing stale OCA-group siblings before placing the SELL. "Broker-only" means the symbol has no `ManagedPosition` in `_managed_positions` — typically EOD Pass 2 zombie cleanup, startup zombie flatten, or post-`reconstruct_from_broker` paths. Without this clearance, a stale yesterday-bracket child could fill against today's flatten SELL and produce an unintended short (the same DEF-204 fill-side mechanism Sessions 1a/1b address for the managed-position paths).

The fix is a strict precondition: invoke `broker.cancel_all_orders(symbol=X, await_propagation=True)` BEFORE the SELL placement, with a 2s timeout. On `CancelPropagationTimeout`, abort the SELL and emit a `cancel_propagation_timeout` SystemAlertEvent — the position remains as a phantom long with no working stop until operator intervention. **This is the intended trade-off** (see Failure Mode below).

Additionally, add a contract docstring to `reconstruct_from_broker()` documenting that it is currently STARTUP-ONLY and that future RECONNECT_MID_SESSION callers MUST add a `ReconstructContext` parameter — because the unconditional `cancel_all_orders(symbol)` is correct only at startup (clears yesterday's stale OCA siblings); a mid-session reconnect would WIPE OUT today's working bracket children that must be preserved.

## Failure Mode Documentation (Item 2 — MEDIUM #7 disposition)

**Critical context for implementers and reviewers:** Session 1c changes the failure mode of EOD Pass 2's `_flatten_unknown_position` path.

- **Prior behavior:** EOD Pass 2 placed the flatten SELL unconditionally on detecting a zombie position. Risk: stale OCA siblings could fill against the SELL, producing a phantom short (DEF-204 mechanism).
- **Post-Session-1c behavior:** EOD Pass 2 first calls `cancel_all_orders(symbol, await_propagation=True)` with a 2s timeout. On success, the SELL proceeds; on `CancelPropagationTimeout`, the SELL is **aborted**, a `cancel_propagation_timeout` alert fires, and the position remains at the broker as a phantom long with no working stop.

**This is the intended trade-off.** Phantom shorts (the bug being fixed) compound risk asymmetrically — short exposure on a runaway upside can produce unbounded loss. Leaked longs (the new failure mode) are bounded exposure (the long position size itself), albeit with no automated stop.

**Operator response when `cancel_propagation_timeout` alert fires for an EOD-flatten path symbol:** manually flatten via `scripts/ibkr_close_all_positions.py` before the next session begins. The runbook at `docs/live-operations.md` "Phantom-Short Gate Diagnosis and Clearance" (added by Session 2d in B22 of doc-update-checklist) covers operator steps; a cross-reference to the cancel-timeout context will be added during sprint-close doc-sync.

This failure-mode shift MUST be exercised by Test 7 below.

## Requirements

1. **Modify `_flatten_unknown_position` at `argus/execution/order_manager.py:1920`:**

   - BEFORE the existing `_broker.place_order(... side=OrderSide.SELL ...)` call, add:

     ```python
     # OCA-EXEMPT: broker-only path — no ManagedPosition exists; safety
     # comes from cancelling stale yesterday OCA siblings before SELL.
     try:
         await self._broker.cancel_all_orders(
             symbol=symbol, await_propagation=True
         )
     except CancelPropagationTimeout as e:
         self._logger.error(
             "EOD Pass 2 flatten ABORTED for %s: cancel propagation timeout — "
             "phantom long remains at broker with no working stop. Operator "
             "must run scripts/ibkr_close_all_positions.py before next session.",
             symbol,
         )
         self._emit_system_alert(
             alert_type="cancel_propagation_timeout",
             severity="critical",
             source="order_manager._flatten_unknown_position",
             message=(
                 f"EOD Pass 2 flatten of zombie position aborted for {symbol}: "
                 f"cancel_all_orders did not propagate within 2s. Position "
                 f"remains long at broker with no automated stop. Manual "
                 f"flatten required."
             ),
             metadata={"symbol": symbol, "shares": shares, "stage": "eod_pass2"},
         )
         return  # do NOT place SELL; abort cleanly
     ```

   - The `# OCA-EXEMPT:` marker is required so Session 1b's grep regression guard `test_no_sell_without_oca_when_managed_position_has_oca` permits the SELL that follows.

   - The `_emit_system_alert` helper invocation should match the existing alert-emission pattern in `order_manager.py` (likely already used by DEF-199 A1 fix or similar). If no helper exists, emit `SystemAlertEvent` directly via the event bus the OrderManager holds. Verify the pattern by grepping for existing `SystemAlertEvent` emissions in `order_manager.py`.

   - DO NOT modify the SELL placement itself or the `_managed_positions` cleanup that follows. The cancel-then-SELL gating is the only addition.

2. **Modify `_drain_startup_flatten_queue` at `argus/execution/order_manager.py:2021`:**

   - Same pattern as Requirement 1, but the alert metadata `stage="startup_zombie_flatten"` and the log/message text reflects startup context.
   - Same `# OCA-EXEMPT:` marker.
   - On `CancelPropagationTimeout`: log ERROR, emit alert, skip the SELL for this symbol, **continue draining the queue** for remaining symbols. Do NOT halt the entire startup-flatten loop on one symbol's timeout.

3. **Modify `reconstruct_from_broker` at `argus/execution/order_manager.py:1813`:**

   - For each symbol being reconstructed, call `cancel_all_orders(symbol=X, await_propagation=True)` BEFORE wiring the position into `_managed_positions`.
   - On `CancelPropagationTimeout` for a single symbol: log ERROR, emit alert with `stage="reconstruct_from_broker"`, **skip wiring that symbol** into `_managed_positions`, and **continue with remaining symbols**.
   - **No SELL is placed in this path** — `reconstruct_from_broker` is a wire-up function, not a flatten path. The `# OCA-EXEMPT:` marker is therefore not technically required here (no SELL placement), but add an explanatory comment:

     ```python
     # SAFETY: cancel stale yesterday OCA siblings BEFORE wiring this
     # broker-confirmed position into _managed_positions. Session 1c (D4).
     # See docstring re: STARTUP_ONLY contract.
     ```

4. **Add contract docstring to `reconstruct_from_broker()` (B3 requirement):**

   The function's existing docstring (if any) is preserved or extended. Add the following block at the top of the docstring (verbatim from sprint-spec.md §D4):

   ```python
   """
   ... [existing docstring summary, if any] ...

   STARTUP-ONLY CONTRACT (added Sprint 31.91 Session 1c):

   This function is currently STARTUP-ONLY and is called exactly once at
   ARGUS boot via `argus/main.py:1081` (gated by `_startup_flatten_disabled`).
   The unconditional `cancel_all_orders(symbol)` invocation is correct ONLY
   in this startup context — it clears stale yesterday's OCA siblings before
   today's session begins.

   Future callers MUST add a context parameter (e.g., `ReconstructContext`)
   distinguishing STARTUP_FRESH from RECONNECT_MID_SESSION. The
   RECONNECT_MID_SESSION path MUST NOT invoke `cancel_all_orders` —
   yesterday's working bracket children are LIVE this-session orders that
   must be preserved.

   Sprint 31.93 (DEF-194/195/196 reconnect-recovery) is the natural sprint
   to add this differentiation. Until then, ARGUS does not support
   mid-session reconnect; operator daily-flatten remains the safety net.
   """
   ```

   This docstring is contractual: future maintainers cannot wire a
   reconnect-recovery caller without first adding the context parameter.

5. **Update mocks (~1 mock file):**

   The test fixtures that mock `OrderManager._broker` likely need a `cancel_all_orders` mock that supports `await_propagation=True`. Session 0 added the API to the ABC; Session 1a/1b consumers used it indirectly via SimulatedBroker. Session 1c is the first sprint session to invoke it on broker-only paths in the OrderManager; existing test mocks may need:

   - `MagicMock` / `AsyncMock` setup for `cancel_all_orders(symbol=..., await_propagation=True)`
   - A way to inject `CancelPropagationTimeout` for test 7 below

   The mock update is scoped to whatever fixture file is shared across the new tests below — typically a `conftest.py` in `tests/execution/` or a shared `BrokerMockFactory`. Per RULE-007, do NOT broaden the mock fixture beyond what these tests require.

6. **DEC-369 broker-confirmed immunity preserved.** Confirm via inspection (and Tier 2 review) that Session 1c does NOT auto-close any `_broker_confirmed=True` position. The orphan loop at `order_manager.py:3038-3039` (extended in Session 2b.1) is untouched here; Session 1c only adds cancel-then-SELL/wire safety to the 3 broker-only entry points. Specifically: `reconstruct_from_broker()` wires positions into `_managed_positions` with `_broker_confirmed=True`; the cancel call BEFORE wiring does not close the position, only cancels stale orders.

7. **No edits to do-not-modify regions.** In particular:

   - `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix) — zero edits. The EOD Pass 2 loop at `:1705-1755` reads from / calls `_flatten_unknown_position` but the loop body itself is not modified. Tier 2 will verify with `git diff`.
   - `argus/main.py` — zero edits. Note: invariant 15 grants Session 1c a SCOPED exception **only for the body of `reconstruct_from_broker()` in `order_manager.py`**, NOT for `main.py`'s call site at `:1081`. The gate (`_startup_flatten_disabled`) and call site stay exactly as they are; the docstring contract clarifies the call site's contractual STARTUP_ONLY assumption without modifying its code.
   - `argus/execution/alpaca_broker.py`, `argus/data/alpaca_data_service.py`, `argus/models/trading.py`, `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`, `workflow/` — zero edits.

## Tests (~6 new + 1 mock update; aim for green CI)

Each test lives under `tests/execution/` (or wherever the existing OrderManager tests reside; verify via `grep -rn "_flatten_unknown_position" tests/` to find the closest neighborhood).

1. **`test_flatten_unknown_position_calls_cancel_all_orders_first`**
   - Setup: mock broker; inject a "zombie" symbol into the EOD Pass 2 path; mock `cancel_all_orders(symbol, await_propagation=True)` to succeed (return 0).
   - Assertion: `cancel_all_orders` called BEFORE `place_order`. Use `mock.call_args_list` ordering.
   - Assertion: `cancel_all_orders` invoked with `symbol=<zombie_symbol>` and `await_propagation=True` keyword.

2. **`test_drain_startup_flatten_queue_calls_cancel_all_orders_first`**
   - Setup: queue 3 symbols into the startup-flatten queue; mock `cancel_all_orders` to succeed for all.
   - Assertion: each symbol triggers `cancel_all_orders` before its SELL.
   - Assertion: order is preserved (drain semantics intact); no symbol gets a SELL without first getting a cancel.

3. **`test_reconstruct_from_broker_calls_cancel_all_orders_per_symbol`**
   - Setup: mock broker `get_positions()` to return 2 positions (e.g., AAPL long, MSFT long); mock `cancel_all_orders` to succeed.
   - Assertion: `cancel_all_orders` called once per symbol BEFORE either gets wired into `_managed_positions`.
   - Assertion: both positions appear in `_managed_positions` after the call returns; both have `_broker_confirmed=True`.

4. **`test_eod_pass2_stale_oca_cleared_before_sell`**
   - Higher-level integration test: simulate EOD Pass 2 with a zombie symbol that has 2 stale working orders at the (mock) broker.
   - Assertion: after `_flatten_unknown_position` returns successfully, `cancel_all_orders` was called and the SELL was placed.
   - Assertion: the SELL Order placed has no `ocaGroup` set (broker-only path is not threaded into an OCA group; safety comes from clearing siblings, not joining a group).

5. **`test_reconstruct_orphaned_oca_cleared`**
   - Setup: mock broker reports a position; the broker also has a stale `STP` working order from yesterday for that symbol.
   - Assertion: `cancel_all_orders(symbol, await_propagation=True)` was invoked; the position is wired into `_managed_positions` with `oca_group_id=None` (no OCA reconstruction across restart — the spec is explicit that bracket OCA grouping is per-bracket-placement, not reconstructed).

6. **`test_cancel_propagation_timeout_aborts_sell_and_emits_alert`**
   - Setup: mock `cancel_all_orders(symbol, await_propagation=True)` to raise `CancelPropagationTimeout`. Trigger via `_flatten_unknown_position`.
   - Assertion: `place_order` was NOT called.
   - Assertion: `SystemAlertEvent` with `alert_type="cancel_propagation_timeout"`, `severity="critical"` was emitted exactly once on the event bus.
   - Assertion: the function returns cleanly (no exception bubbles up); the next call in the EOD Pass 2 loop can proceed for a different symbol.

7. **`test_eod_pass2_cancel_timeout_aborts_sell_emits_alert_no_phantom_short` (Item 2 — MEDIUM #7)**
   - Setup: simulate EOD Pass 2 with a zombie LONG position (e.g., `Position(side=OrderSide.BUY, shares=100)`); mock `cancel_all_orders` to raise `CancelPropagationTimeout`.
   - Assertion: `place_order` is NOT called for this symbol — that's the failure-mode point. Placing the SELL incorrectly is the bug the abort prevents.
   - Assertion: `cancel_propagation_timeout` alert fires.
   - Assertion: the position is NOT marked closed in any tracking structure (it's still a phantom long; the alert is the operator's signal to manually flatten).
   - **Docstring on the test:** `"""MEDIUM #7: cancel-timeout escape hatch in _flatten_unknown_position leaves position un-flattened (intended trade-off; phantom long with no stop is a bounded exposure preferable to an incorrect SELL that would create an unbounded phantom short). Operator manually flattens via scripts/ibkr_close_all_positions.py."""`
   - **Comment in the test body** linking to PHASE-D-OPEN-ITEMS Item 2 + sprint-spec.md §D4 + this implementation prompt's Failure Mode section.

8. **(MOCK UPDATE)** Update the shared broker mock fixture (typically in `tests/execution/conftest.py` or `tests/conftest.py`) so that:
   - `cancel_all_orders` is a mockable async method accepting `symbol` and `await_propagation`.
   - There's a fixture or factory entry to inject `CancelPropagationTimeout` for test 6 + test 7.

   Per RULE-019, this mock update should not delete or skip existing tests. Existing tests that don't touch `cancel_all_orders` continue to pass unchanged.

## Definition of Done

- [ ] All 3 functions invoke `cancel_all_orders(symbol, await_propagation=True)` BEFORE SELL placement (or BEFORE wiring, for `reconstruct_from_broker`).
- [ ] On `CancelPropagationTimeout`: SELL aborted (or wiring skipped); `cancel_propagation_timeout` SystemAlertEvent emitted with severity=critical and stage metadata.
- [ ] `reconstruct_from_broker()` docstring documents STARTUP_ONLY contract + future-caller `ReconstructContext` requirement (verbatim from spec §D4).
- [ ] DEC-369 broker-confirmed immunity preserved (no auto-close of `_broker_confirmed=True` positions).
- [ ] 6 new tests + 1 mock update added; all passing.
- [ ] Item 2 test (test 7) covers cancel-timeout failure mode and docstring/body comments link to PHASE-D-OPEN-ITEMS Item 2.
- [ ] `# OCA-EXEMPT:` markers added at the 2 SELL-placement sites (`_flatten_unknown_position`, `_drain_startup_flatten_queue`); the `reconstruct_from_broker` site uses an explanatory `# SAFETY:` comment (no SELL there).
- [ ] Session 1b's grep regression guard `test_no_sell_without_oca_when_managed_position_has_oca` still passes (the `# OCA-EXEMPT:` markers correctly exempt the new sites).
- [ ] CI green; pytest baseline ≥ 5,080 + 6 = 5,086 (Session 1b's adds confirmed; Session 1c adds 6 new + 1 mock update).
- [ ] Tier 2 review (backend safety reviewer) verdict CLEAR.
- [ ] All do-not-modify list items show zero `git diff` (with the scoped exception in invariant 15: `reconstruct_from_broker()` body in `order_manager.py` is permitted to grow per Session 1c's spec).
- [ ] Close-out report written to `docs/sprints/sprint-31.91-reconciliation-drift/session-1c-closeout.md` with the structure below.
- [ ] Close-out anticipates Tier 3 #1 review (see "Close-Out Tier-3 Readiness" section).

## Close-Out Report

Write `docs/sprints/sprint-31.91-reconciliation-drift/session-1c-closeout.md` containing:

1. **Files modified** — exact paths + line ranges.
2. **Tests added** — list of 7 entries (6 tests + 1 mock fixture update). Per-entry note on what each tests / why it cannot be deleted.
3. **`git diff --stat`** output snippet.
4. **Test evidence** — output of `python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q` showing scoped suite passes; output of one full-suite run (`python -m pytest --ignore=tests/test_main.py -n auto -q`) confirming baseline holds.
5. **Do-not-modify audit** — `git diff` with explicit assertions for each protected file/region.
6. **Failure mode documentation cross-reference** — note that the cancel-timeout failure mode is documented in this prompt's "Failure Mode Documentation" section, anchored by test 7, and will be added to `docs/live-operations.md` at sprint-close doc-sync (B22 cross-reference).
7. **Discovered Edge Cases** — any deviation from the spec or unexpected interaction surfaced during implementation. If empty, write "None."
8. **Deferred Items (RULE-007)** — bugs/improvements outside scope; if empty, write "None."
9. **Verdict JSON block:**

   ```json
   {
     "session": "1c",
     "verdict": "PROPOSED_CLEAR",
     "tests_added": 7,
     "tests_total_after": <fill>,
     "files_modified": ["argus/execution/order_manager.py", "tests/execution/...", "tests/.../conftest.py"],
     "donotmodify_violations": 0,
     "tier_3_readiness": "READY"
   }
   ```

10. **Close-Out Tier-3 Readiness section** — anticipating Tier 3 architectural review #1, summarize the OCA architecture state at the end of Session 1c:

    - **API contract (Session 0):** `Broker.cancel_all_orders(symbol, *, await_propagation=False) -> int` extension; `CancelPropagationTimeout` exception; ABC + IBKRBroker + SimulatedBroker + AlpacaBroker(deprecation) implementations.
    - **Bracket OCA (Session 1a):** `ocaGroup=f"oca_{parent_ulid}"`, `ocaType=1` on all bracket children at `IBKRBroker.place_bracket_order`; `ManagedPosition.oca_group_id` field; defensive Error 201 / "OCA group is already filled" handling.
    - **Standalone-SELL OCA (Session 1b):** 4 paths threaded — `_trail_flatten`, `_escalation_update_stop`, `_resubmit_stop_with_retry`, `_flatten_position`; grep regression guard with `# OCA-EXEMPT:` exemption mechanism; graceful Error 201 handling.
    - **Broker-only safety (Session 1c, this session):** 3 paths — `_flatten_unknown_position`, `_drain_startup_flatten_queue`, `reconstruct_from_broker`; cancel-before-SELL with 2s `await_propagation`; `CancelPropagationTimeout` aborts SELL + alert; `reconstruct_from_broker` startup-only contract docstring.

    Then list, for the Tier 3 reviewer's convenience, the 4 most likely architectural questions and your answers:

    - **Q1:** Does Session 1c's cancel-before-SELL gate interact with DEC-117 atomic bracket invariant?
      **A:** No. DEC-117 governs bracket placement (parent-fails → all children cancelled). Session 1c gates broker-only flatten/wire paths, which by definition have no `ManagedPosition` and therefore no atomic-bracket relationship to preserve.
    - **Q2:** Does the 2s `await_propagation` timeout introduce a new failure mode that wasn't bounded in Sessions 0/1a/1b?
      **A:** Yes — the leaked-long failure mode (phantom long with no stop). Documented in the Failure Mode section above; covered by test 7. Operator response is manual flatten via existing tooling (`scripts/ibkr_close_all_positions.py`), which the daily mitigation already prescribes through the sprint window.
    - **Q3:** Why is `reconstruct_from_broker`'s contract docstring contractual rather than a runtime check?
      **A:** Adding a runtime check (e.g., `assert context == STARTUP_FRESH`) would require a context parameter, which Session 1c explicitly defers to Sprint 31.93 (DEF-194/195/196 reconnect-recovery sprint). The docstring is the bridging mechanism: future maintainers wiring a reconnect path see the contractual STARTUP_ONLY warning before they propagate the bug.
    - **Q4:** Is the `# OCA-EXEMPT:` mechanism robust against future SELL additions in broker-only paths?
      **A:** Mostly. Session 1b's grep regression guard checks for `_broker.place_order(... SELL ...)` calls without OCA threading; the `# OCA-EXEMPT: <reason>` comment provides an opt-out. Future broker-only SELL paths must either (a) be exempt with the marker (legitimate broker-only safety) or (b) be threaded with OCA. The grep test is the structural enforcement; a future reviewer who adds a SELL without either is forced to confront the choice.

## Tier 2 Review Invocation

After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.91-reconciliation-drift/session-1c-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test commands:
   - Scoped: `python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q`
   - Full: `python -m pytest --ignore=tests/test_main.py -n auto -q` (DEC-328 — this is the LAST session before Tier 3 #1; full suite is appropriate at this gate)
5. Files that should NOT have been modified (explicit list for `git diff` audit):
   - `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix)
   - `argus/execution/order_manager.py:1705-1755` EOD Pass 2 loop body (only the called function `_flatten_unknown_position` is modified)
   - `argus/execution/ibkr_broker.py` (Session 1a was the IBKR-broker-touching session)
   - `argus/main.py` (the call site at `:1081` and the `_startup_flatten_disabled` gate stay exactly as-is)
   - `argus/models/trading.py`
   - `argus/execution/alpaca_broker.py`
   - `argus/data/alpaca_data_service.py`
   - `argus/execution/broker.py` (Session 0 finalized this; Session 1c only consumes the API)
   - `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`
   - `workflow/` submodule

The @reviewer must use the **backend safety reviewer** template (`templates/review-prompt.md`).

The @reviewer will produce its review report at:

```
docs/sprints/sprint-31.91-reconciliation-drift/session-1c-review.md
```

## Post-Review Fix Documentation

Same pattern as Sessions 0/1a/1b. If @reviewer reports CONCERNS and you fix within session, append "Post-Review Fixes" / "Post-Review Resolution" sections and update verdict JSON to `CONCERNS_RESOLVED`.

If @reviewer reports ESCALATE: halt; do NOT fix forward without operator dispositioning. Tier 3 #1 review is the next gate; an unresolved Tier 2 ESCALATE here would compound into Tier 3.

## Session-Specific Review Focus (for @reviewer)

1. **Cancel-before-SELL ordering.** For each of the 3 functions, verify by `git diff` reading that `cancel_all_orders(...)` appears textually BEFORE `place_order(...)` (or BEFORE `_managed_positions[symbol] = ...` for `reconstruct_from_broker`). Run tests 1, 2, 3 — all should fail if ordering is reversed.

2. **`await_propagation=True` is set everywhere.** Grep the diff: every new `cancel_all_orders` call must include `await_propagation=True` as a keyword argument. The default is `False` (DEC-364 / Session 0); using the default here would be a silent regression.

3. **`CancelPropagationTimeout` handling.** For each of the 3 functions, verify:
   - The exception is caught.
   - The SELL (or wiring) is aborted.
   - `SystemAlertEvent` is emitted with `severity="critical"`, `alert_type="cancel_propagation_timeout"`, and stage-specific metadata.
   - In `_drain_startup_flatten_queue` and `reconstruct_from_broker`, processing **continues** for the next symbol (no early-return that would skip queued symbols).

4. **Reconstruct docstring is verbatim.** Compare the docstring text to sprint-spec.md §D4 lines 118–136. Any rephrasing or summarization is a concern; the contract is intentionally precise about the `ReconstructContext` requirement.

5. **`# OCA-EXEMPT:` markers present and well-formed.** Two markers should be present (in `_flatten_unknown_position` and `_drain_startup_flatten_queue`); both should explain WHY the path is exempt (broker-only, no `ManagedPosition`). A bare `# OCA-EXEMPT:` with no reason is a concern.

6. **Test 7 failure-mode coverage.** Verify test 7 exercises:
   - `Position(side=OrderSide.BUY, shares=N)` (a long zombie, NOT a short — phantom shorts are what we're avoiding by aborting)
   - `cancel_all_orders` raises `CancelPropagationTimeout`
   - `place_order` is NOT called
   - The position is NOT marked closed in any tracking structure (the failure mode is "leaked long," not "cleanly closed")

7. **Mock fixture update is scoped.** The mock fixture additions (likely in a `conftest.py`) should add `cancel_all_orders` mocking + a way to inject `CancelPropagationTimeout`. They should NOT modify existing fixtures used by tests that don't touch `cancel_all_orders` (RULE-019).

8. **Sprint 31.93 cross-reference present.** The reconstruct docstring should explicitly name "Sprint 31.93 (DEF-194/195/196 reconnect-recovery)" as the future home of the `ReconstructContext` differentiation. Reviewer verifies the cross-reference is present and matches Sprint Spec §D4.

9. **DEF-199 A1 fix unchanged.** Run `test_short_position_is_not_flattened_by_pass2` (and Pass 1 sibling) and confirm pass. The EOD Pass 2 loop calls `_flatten_unknown_position`, which is now gated by `cancel_all_orders`; test 4 (`test_eod_pass2_stale_oca_cleared_before_sell`) and the existing DEF-199 anti-regression test must BOTH pass.

10. **Session 1b grep regression guard still green.** Run `test_no_sell_without_oca_when_managed_position_has_oca`. The two `# OCA-EXEMPT:` markers added in Session 1c should be tolerated (the test recognizes the marker per Session 1b's design). If the test fails on the new sites, the marker is malformed or the test is broken.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`.

Of particular relevance to Session 1c:

- **Invariant 1 (DEF-199 A1 fix detects + refuses 100% of phantom shorts at EOD):** PASS — verify zero edits to `order_manager.py:1670-1750`.
- **Invariant 2 (DEF-199 A1 EOD Pass 1 retry side check):** PASS — same check as Inv. 1 plus running the Pass 1 anti-regression test.
- **Invariant 3 (DEF-158 dup-SELL prevention):** PASS — Session 1c does not modify `_check_flatten_pending_timeouts`.
- **Invariant 4 (DEC-117 atomic bracket invariant):** PASS — Session 1c does not touch bracket placement.
- **Invariant 5 (5,080 pytest baseline holds):** Pytest baseline after Session 1c expected ≥ 5,086 (5,080 baseline + Session 0 ~6 + Session 1a ~8 + Session 1b ~8 + Session 1c ~6 = `~5,108` modulo any overlap; verify in close-out test evidence).
- **Invariant 14 (Monotonic-safety property):** Row "After Session 1c" — OCA bracket = YES, OCA standalone (4) = YES, Broker-only safety = YES, Restart safety = YES, all others = NO.
- **Invariant 15 (do-not-modify list untouched):** PASS — verify the explicit list above. The scoped exception for the `reconstruct_from_broker()` body in `order_manager.py` is documented per invariant 15's "Session 1c reconstruct-safety" exception.
- **Invariant 21 (SimulatedBroker OCA-assertion tautology guard):** Lands at Session 0 close-out; verify still passing.

## Sprint-Level Escalation Criteria (for @reviewer)

Of particular relevance to Session 1c:

- **A1** (Tier 3 #1 architectural review fires AFTER this session lands cleanly).
- **A2** (Tier 2 CONCERNS or ESCALATE).
- **A3** (post-merge paper session shows phantom-short accumulation — would imply the OCA architecture is not yet complete despite Sessions 0/1a/1b/1c landing).
- **A8** (bracket placement performance regression — Session 1a's bracket OCA is the trigger surface; Session 1c does not directly affect bracket placement, but the Tier 3 review will assess the combined diff).
- **B1, B3, B4, B5, B6** — standard halt conditions. Note: B5 (DISCOVERY line numbers drift > 5 lines) is especially relevant for this session because 1c touches three discrete functions identified by line number (`:1813`, `:1920`, `:2021`) — verify each at pre-flight.
- **C5** (uncertain whether a change crosses a do-not-modify boundary) — the `main.py:1081` call-site is structurally close to the `reconstruct_from_broker()` body modification; verify that `main.py` shows zero diff.

---

*End Sprint 31.91 Session 1c implementation prompt.*
