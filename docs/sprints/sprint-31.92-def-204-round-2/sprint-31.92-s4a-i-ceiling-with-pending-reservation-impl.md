# Sprint 31.92, Session S4a-i: Long-Only SELL-Volume Ceiling — Implementation per H-R2-1 Atomic Method + AC2.7 Watchdog Auto-Activation per Decision 4

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt. RULE-038 (grep-verify discipline), RULE-042 (`getattr` silent-default anti-pattern), RULE-043 (`except Exception:` swallowing test signals), and RULE-050 (CI-green discipline) apply with particular force.

2. Read these files to load context:
   - `argus/execution/order_manager.py` — exit-side hot zones: `ManagedPosition` dataclass, `on_fill` method, the 5 standalone-SELL emit sites (`_trail_flatten`, `_escalation_update_stop`, `_resubmit_stop_with_retry`, `_flatten_position`, `_check_flatten_pending_timeouts`), and `reconstruct_from_broker`. Anchor by function names (line numbers DIRECTIONAL ONLY per protocol v1.2.0+).
   - `argus/core/alert_auto_resolution.py` — existing `POLICY_TABLE` (13 entries pattern post-Sprint-31.91). The 14th entry for `sell_ceiling_violation` lands here.
   - `tests/api/test_policy_table_exhaustiveness.py` — the AST regression guard pattern from DEF-219. The exhaustiveness count assertion must update from 13 → 14.
   - `argus/core/events.py::SystemAlertEvent` — schema for the new alert.
   - The S3b close-out artifact: `docs/sprints/sprint-31.92-def-204-round-2/session-s3b-closeout.md`. **Critical:** S3b adds `halt_entry_until_operator_ack: bool = False` to `ManagedPosition`. S4a-i references that field but does NOT re-add it; verify field-ownership during pre-flight per the field-add-ordering note below.
   - The sprint spec § "Acceptance Criteria" Deliverable 3 (AC3.1 through AC3.9) and the AC2.7 watchdog auto-activation per Decision 4.
   - `docs/sprints/sprint-31.92-def-204-round-2/round-3-disposition.md` § 3.2 (H-R3-2 — watchdog `auto`→`enabled` flip semantics: in-memory only, asyncio.Lock-guarded, idempotent, logged transition).

3. Run the test baseline (DEC-328 — Session 7+ of sprint, scoped):

   ```
   python -m pytest tests/execution/order_manager/ tests/api/test_policy_table_exhaustiveness.py -n auto -q
   ```

   Expected: all passing (full suite was confirmed by S3b's close-out). Note: in autonomous mode, the expected test count is dynamically adjusted by the runner based on the previous session's actual results; the count above is the planning-time estimate.

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** from the "Files to Modify" section below. For each entry, run the verbatim grep-verify command and confirm the anchor still resolves to the expected location. If drift is detected, disclose under RULE-038 in the close-out and proceed against the actual structural anchors. If the anchor is not found at all, HALT and request operator disposition rather than guess.

6. Verify S3b's deliverables are present on `main`:

   ```bash
   grep -n "halt_entry_until_operator_ack" argus/execution/order_manager.py
   grep -n "_branch4_last_alert_at" argus/execution/order_manager.py
   grep -n "refresh_positions" argus/execution/broker.py
   grep -n "_REFRESH_POSITIONS_COALESCE_WINDOW_SECONDS" argus/execution/ibkr_broker.py
   grep -n "_handle_suppression_timeout_for_position\|_read_positions_post_refresh" argus/execution/order_manager.py
   ```

   All five anchors must match. If any are missing, halt — S3b has not landed yet.

7. **Field-add-ordering note (RULE-038):** Per S3b's prompt, `halt_entry_until_operator_ack: bool = False` is added to `ManagedPosition` at S3b. S4a-i adds the OTHER three new fields (`cumulative_pending_sell_shares: int = 0`, `cumulative_sold_shares: int = 0`, `is_reconstructed: bool = False`). If S3b's close-out documented adding `is_reconstructed` as forward-compat (per S3b's prompt allowance), DO NOT re-add it — only assign to it inside `reconstruct_from_broker`. Disclose the field-ownership in S4a-i's close-out's RULE-038 section.

## Objective

Add `ManagedPosition.cumulative_pending_sell_shares: int = 0`, `cumulative_sold_shares: int = 0`, and `is_reconstructed: bool = False` fields (the fourth field, `halt_entry_until_operator_ack`, was added at S3b); implement atomic synchronous `_reserve_pending_or_fail()` method per H-R2-1 (with AST-no-await guard + mocked-await injection regression test); implement `_check_sell_ceiling()` helper checking `pending + sold + requested ≤ shares_total` with `is_stop_replacement: bool` exemption per H-R2-5 (exemption permitted ONLY at `_resubmit_stop_with_retry` normal-retry path); guard 5 standalone-SELL emit sites per AC3.2; refuse ALL ARGUS-emitted SELLs on `is_reconstructed=True` (early return short-circuit); wire `sell_ceiling_violation` POLICY_TABLE entry as the 14th entry; update the AST exhaustiveness regression guard from 13 → 14 entries; auto-activate AC2.7 `_pending_sell_age_seconds` watchdog from `auto` to `enabled` on first observed `case_a_in_production` event per Decision 4 (config toggle `pending_sell_age_watchdog_enabled: auto` flips to `enabled` on first case-A event; in-memory only; `asyncio.Lock`-guarded; restart resets per H-R3-2).

## Requirements

1. **Add three new fields to `ManagedPosition` dataclass** in `argus/execution/order_manager.py`:

   ```python
   @dataclass
   class ManagedPosition:
       # ... existing fields, including (added at S3b):
       #   halt_entry_until_operator_ack: bool = False
       cumulative_pending_sell_shares: int = 0  # AC3.1 / regression invariant 13/20
       cumulative_sold_shares: int = 0  # AC3.1 / regression invariant 13/20
       is_reconstructed: bool = False  # AC3.7 / regression invariant 19
   ```

   All three are in-memory only (no SQLite persistence — DEF-209 deferred to Sprint 35+ Learning Loop V2 per SbC §"Out of Scope" #20–#21). Use `int` not `int64` or `Decimal` (SbC §"Edge Cases to Reject" #3 — overflow infeasible).

2. **Implement atomic synchronous `_reserve_pending_or_fail()` method** on `OrderManager` per H-R2-1 / AC3.1:

   ```python
   def _reserve_pending_or_fail(
       self,
       position: ManagedPosition,
       requested_qty: int,
       *,
       is_stop_replacement: bool = False,
   ) -> bool:
       """Atomic synchronous reserve-or-fail per H-R2-1.

       This method is the place-time reservation entry point. Per AC3.1
       state transition #1, the pending counter is incremented BEFORE
       any await. The method body is SYNCHRONOUS — no await between the
       ceiling check and the reserve increment. The AST-no-await guard
       at S4a-i and the FAI #11 callsite-enumeration check at S4a-ii
       enforce this invariant structurally.

       Per H-R2-5: is_stop_replacement=True bypasses the ceiling check.
       This exemption is permitted ONLY at _resubmit_stop_with_retry's
       normal-retry path (NOT the emergency-flatten branch). The AST
       callsite-scan regression at S4a-ii (FAI #8 + Decision 3
       reflective-pattern coverage) enforces this.

       Per AC3.7: if position.is_reconstructed == True, return False
       unconditionally — refuse ALL ARGUS-emitted SELLs on reconstructed
       positions.

       Per AC3.8: when long_only_sell_ceiling_enabled == False, return
       True unconditionally (config-gated, fail-closed by default).

       Returns:
           True if reservation succeeded (pending was incremented).
           False if ceiling would be violated OR position is reconstructed.
       """
       if not self._config.long_only_sell_ceiling_enabled:
           # AC3.8: config-gate disabled returns True unconditionally.
           position.cumulative_pending_sell_shares += requested_qty
           return True

       if position.is_reconstructed:
           # AC3.7: refuse ALL SELLs on reconstructed positions.
           return False

       if is_stop_replacement:
           # H-R2-5 exemption — bypass ceiling, increment pending.
           position.cumulative_pending_sell_shares += requested_qty
           return True

       # Synchronous multi-attribute read; no await between read and write.
       pending = position.cumulative_pending_sell_shares
       sold = position.cumulative_sold_shares
       total = position.shares_total
       if pending + sold + requested_qty > total:
           return False  # Caller fires sell_ceiling_violation alert.

       position.cumulative_pending_sell_shares += requested_qty
       return True
   ```

   **Critical:** The method body MUST be synchronous from the moment it reads `position.cumulative_pending_sell_shares` to the moment it writes the increment. NO `await`, NO async DB calls, NO `asyncio.sleep`, NO `await self._lock.acquire()`. The S4a-i AST guard test (`test_no_await_in_reserve_pending_or_fail_body`) walks the source via `ast.parse` and asserts no `ast.Await` node. The mocked-await injection test (`test_reserve_pending_or_fail_race_observable_under_injection`) monkey-patches an `asyncio.sleep(0)` between read and write to assert the race IS observable under injection (proves the test is sensitive enough to catch a regression).

3. **Implement `_check_sell_ceiling` as a thin wrapper** that's separate from the reservation. Per AC3.5 and S4a-ii's multi-attribute-read AST scan (regression invariant 23), keep `_check_sell_ceiling` minimal:

   ```python
   def _check_sell_ceiling(
       self,
       position: ManagedPosition,
       requested_qty: int,
       *,
       is_stop_replacement: bool = False,
   ) -> bool:
       """Per AC3.5: synchronous read-only check; preferred caller is
       _reserve_pending_or_fail (which atomically reserves on success).
       Direct callers exist for diagnostic / read-only contexts. The
       multi-attribute read sequence (pending, sold, requested) MUST
       happen synchronously — S4a-ii's AST guard
       (test_no_await_in_check_sell_ceiling_multi_attribute_read)
       enforces this."""
       if not self._config.long_only_sell_ceiling_enabled:
           return True
       if position.is_reconstructed:
           return False
       if is_stop_replacement:
           return True
       pending = position.cumulative_pending_sell_shares
       sold = position.cumulative_sold_shares
       return (pending + sold + requested_qty) <= position.shares_total
   ```

   Note: the production call sites use `_reserve_pending_or_fail`, not `_check_sell_ceiling` directly — the latter is for tests/diagnostics. The S4a-ii AST scan covers both.

4. **Wire pending-counter mutations in `on_fill`, `on_cancel`, `on_reject`** per AC3.1 state transitions 2–5:

   In `on_fill`:
   ```python
   # State transition #4 (partial-fill transfer) and #5 (full-fill transfer)
   # AC3.1: synchronous decrement of pending + increment of sold,
   # NO await between read and write. S4a-ii's AST guard
   # (test_no_await_between_bookkeeping_read_and_write_in_on_fill)
   # enforces this for both partial-fill and full-fill paths.
   if order.side == OrderSide.SELL:
       # Synchronous transfer:
       position.cumulative_pending_sell_shares -= filled_qty
       position.cumulative_sold_shares += filled_qty
       # NO await between the two mutations above.
   ```

   In `on_cancel`:
   ```python
   # State transition #2 (cancel-time decrement)
   if order.side == OrderSide.SELL and order.qty > 0:
       position.cumulative_pending_sell_shares -= order.qty  # cancelled qty
   ```

   In `on_reject`:
   ```python
   # State transition #3 (reject-time decrement)
   if order.side == OrderSide.SELL and order.qty > 0:
       position.cumulative_pending_sell_shares -= order.qty  # rejected qty
   ```

   **Critical:** all three must be synchronous between read and write. S4a-ii extends the AST regression to all three callback paths (`on_fill`, `on_cancel`, `on_reject`) plus `_on_order_status` plus the `_check_sell_ceiling` multi-attribute read. S4a-i lays the groundwork; S4a-ii enforces.

5. **Guard ONE canonical standalone-SELL emit site at S4a-i** per the session-breakdown's option-δ-prime mitigation. The canonical site is `_trail_flatten`. The remaining 4 sites' coverage lands at S5b composite. At `_trail_flatten`:

   ```python
   # AC3.2: ceiling guard at standalone-SELL emit site.
   # Path #2's _is_locate_suppressed pre-check (S3b) sits BEFORE this;
   # the ceiling guard composes additively.
   if not self._reserve_pending_or_fail(position, requested_qty):
       # Ceiling violation — emit alert per AC3.3.
       await self._event_bus.publish(SystemAlertEvent(
           alert_type="sell_ceiling_violation",
           severity="critical",
           metadata={
               "position_id": position.id,
               "symbol": position.symbol,
               "requested_qty": requested_qty,
               "pending": position.cumulative_pending_sell_shares,
               "sold": position.cumulative_sold_shares,
               "shares_total": position.shares_total,
               "emit_site": "_trail_flatten",
           },
       ))
       logger.critical(
           "sell_ceiling_violation at _trail_flatten for position %s "
           "(pending=%d, sold=%d, requested=%d, total=%d)",
           position.id,
           position.cumulative_pending_sell_shares,
           position.cumulative_sold_shares,
           requested_qty,
           position.shares_total,
       )
       return  # Do NOT proceed to place_order; do NOT increment pending.
   try:
       await self._broker.place_order(...)
   except Exception as exc:
       # Note: locate-rejection handling (S3b) sits inside this except —
       # if locate-rejected, the pending reservation should be DECREMENTED
       # since no SELL actually occurred. Verify the S3b implementation
       # and ensure the decrement happens. (Test 5 / C-1 race exercises this.)
       raise
   ```

   The other 4 sites (`_escalation_update_stop`, `_resubmit_stop_with_retry`, `_flatten_position`, `_check_flatten_pending_timeouts`) get the SAME guard pattern at S5b composite. Per session-breakdown S4a-i scope, only `_trail_flatten` lands at S4a-i.

   **Special case at `_resubmit_stop_with_retry`:** the normal-retry path uses `is_stop_replacement=True` per H-R2-5 (exemption permitted ONLY at this site). The emergency-flatten branch (DEC-372 retry-cap exhausted) uses `is_stop_replacement=False` (no exemption — the emergency SELL competes with other emit sites for the long-quantity budget). This split lands at S5b composite, NOT S4a-i.

6. **Set `is_reconstructed = True` in `reconstruct_from_broker`** per AC3.7 / regression invariant 19. Single-line addition inside the function body (the only modification to `reconstruct_from_broker` permitted by SbC §"Do NOT modify"):

   ```python
   # Inside reconstruct_from_broker, after position object is constructed:
   position.is_reconstructed = True
   ```

   Per AC3.6: also initialize `cumulative_pending_sell_shares = 0`, `cumulative_sold_shares = 0`, `shares_total = abs(broker_position.shares)`. The dataclass defaults handle the first two; the third is the existing initialization (verify during pre-flight that `shares_total` is already populated correctly from `abs(broker_position.shares)`; if not, fix here as part of the AC3.6 initialization).

7. **AC2.7 watchdog auto-activation logic** per Decision 4 + H-R3-2. In `OrderManager`:

   ```python
   # __init__ initialization:
   self._watchdog_enabled_state: str = self._config.pending_sell_age_watchdog_enabled
   # Values: "auto", "enabled", "disabled". "auto" mode flips to
   # "enabled" on first observed case_a_in_production event.
   self._watchdog_state_lock: asyncio.Lock = asyncio.Lock()  # H-R3-2 atomicity

   async def _maybe_auto_activate_watchdog(
       self,
       position: ManagedPosition,
       age_seconds_at_flip: float,
   ) -> None:
       """Per Decision 4 + H-R3-2: flip watchdog from 'auto' to 'enabled'
       on first observed case_a_in_production event. The flip is:
       - in-memory only (no persistence; restart resets to 'auto')
       - asyncio.Lock-guarded (re-entrant flips are no-ops, idempotent)
       - logged via structured INFO log line

       Definition of case_a_in_production (per H-R3-2):
       'first time _pending_sell_age_seconds exceeds threshold AND no
       fill observed AND _locate_suppressed_until[position.id] is set,
       in any position.'
       """
       async with self._watchdog_state_lock:
           if self._watchdog_enabled_state != "auto":
               # Already-flipped or explicitly enabled/disabled — no-op.
               return
           self._watchdog_enabled_state = "enabled"
           logger.info(
               "AC2.7 watchdog auto-flipped from 'auto' to 'enabled' "
               "on first case_a_in_production event "
               "(position=%s, symbol=%s, age=%.1fs)",
               position.id, position.symbol, age_seconds_at_flip,
               extra={
                   "event": "watchdog_auto_to_enabled",
                   "case_a_evidence": {
                       "position_id": position.id,
                       "symbol": position.symbol,
                       "age_seconds_at_flip": age_seconds_at_flip,
                   },
               },
           )
   ```

   The watchdog's actual firing logic (the `now - position.last_sell_emit_time > pending_sell_age_seconds` check) is OUT of S4a-i scope per session-breakdown — only the auto-activation path lands at S4a-i. The watchdog's full firing logic is implicit in the existing AC2.7 wiring at S3a (verify during pre-flight that S3a established the watchdog scaffolding; if not, document the deferral in close-out's "Deferred Items").

   The flip detection trigger (where `_maybe_auto_activate_watchdog` is called from) is the existing watchdog detection path; S4a-i wires the auto-flip into that path. Verify the existing structure during pre-flight.

8. **Add `sell_ceiling_violation` POLICY_TABLE 14th entry** in `argus/core/alert_auto_resolution.py` per AC3.9 / regression invariant 7:

   ```python
   # In build_policy_table() or equivalent:
   "sell_ceiling_violation": PolicyEntry(
       operator_ack_required=True,
       auto_resolution_predicate=None,  # NEVER_AUTO_RESOLVE — manual ack only.
   ),
   ```

   Verify the existing `PolicyEntry` shape during pre-flight; the field names above (`operator_ack_required`, `auto_resolution_predicate`) follow the prompt-cited Round 3 disposition § 3.5 / AC3.9 — confirm against the actual class definition.

9. **Update AST exhaustiveness regression guard** at `tests/api/test_policy_table_exhaustiveness.py` from 13 → 14 expected entries per AC3.9. This test was added at DEF-219 (Sprint 31.91 Impromptu A); confirm the assertion update is the ONLY edit needed (the test file's structure should not change).

## Files to Modify

For each file the session edits, the structural anchor + edit shape + pre-flight grep-verify command are listed below. Line numbers MAY appear as directional cross-references but are NEVER the sole anchor — structural anchors bind per protocol v1.2.0+.

1. `argus/execution/order_manager.py`:
   - Anchor 1: `class ManagedPosition:` dataclass — add 3 new fields (`cumulative_pending_sell_shares`, `cumulative_sold_shares`, `is_reconstructed`). Verify `halt_entry_until_operator_ack` was added at S3b — if not, add it here as part of S4a-i's field-set (4 fields total) and disclose the merge.
   - Anchor 2: insertion point for `_reserve_pending_or_fail` and `_check_sell_ceiling` private methods on `OrderManager`.
   - Anchor 3: function `on_fill` — wire pending decrement + sold increment for SELL fills (state transitions #4 + #5).
   - Anchor 4: function `on_cancel` — wire pending decrement on cancel (state transition #2).
   - Anchor 5: function `on_reject` — wire pending decrement on reject (state transition #3).
   - Anchor 6: function `_trail_flatten` — wire `_reserve_pending_or_fail` guard + `sell_ceiling_violation` alert emission (canonical emit site at S4a-i).
   - Anchor 7: function `reconstruct_from_broker` — single-line addition `position.is_reconstructed = True` AND verify AC3.6 initialization.
   - Anchor 8: `OrderManager.__init__` — initialize `self._watchdog_enabled_state` and `self._watchdog_state_lock`.
   - Anchor 9: insertion point for `_maybe_auto_activate_watchdog` private method.
   - Edit shape: 3 dataclass field additions; 2 new private method insertions; 3 callback-path edits (small additions inside existing handlers); 1 emit-site guard insertion; 1 single-line reconstruct addition; 1 init-state addition; 1 watchdog auto-flip method insertion.
   - Pre-flight grep-verify:
     ```bash
     grep -n "class ManagedPosition\|^@dataclass" argus/execution/order_manager.py | head -5
     grep -n "halt_entry_until_operator_ack" argus/execution/order_manager.py
     grep -n "def on_fill\|def on_cancel\|def on_reject" argus/execution/order_manager.py
     grep -n "def _trail_flatten\|def reconstruct_from_broker" argus/execution/order_manager.py
     grep -n "pending_sell_age_watchdog_enabled" argus/execution/order_manager.py
     # Expected: 1 hit on ManagedPosition; halt_entry_until_operator_ack
     # ≥1 hit (S3b deliverable); 3 hits on the callback methods; 2 hits
     # on the emit-site/reconstruct functions.
     ```

2. `argus/core/alert_auto_resolution.py`:
   - Anchor: `POLICY_TABLE` (or `build_policy_table` function — verify the actual name during pre-flight) — add `sell_ceiling_violation` 14th entry.
   - Edit shape: insertion of one new dict entry / PolicyEntry construction.
   - Pre-flight grep-verify:
     ```bash
     grep -n "POLICY_TABLE\|build_policy_table\|PolicyEntry" argus/core/alert_auto_resolution.py | head -10
     # Expected: ≥1 hit on POLICY_TABLE or build_policy_table; ≥1 hit
     # on PolicyEntry. Confirm the existing 13 entries pre-S4a-i.
     ```

3. `tests/api/test_policy_table_exhaustiveness.py`:
   - Anchor: existing assertion that asserts the entry count.
   - Edit shape: update the count from 13 → 14 + add a check that `sell_ceiling_violation` is among the keys.
   - Pre-flight grep-verify:
     ```bash
     grep -n "13\|len(\|expected.*entries\|POLICY_TABLE" tests/api/test_policy_table_exhaustiveness.py | head -10
     # Identify the existing count assertion; update precisely.
     ```

4. `tests/execution/order_manager/test_def204_round2_ceiling.py` (NEW FILE):
   - Anchor: file does not exist; CREATE.
   - Edit shape: new test file ~140 LOC for 7 effective tests (see Test Targets below).
   - Pre-flight grep-verify:
     ```bash
     ls tests/execution/order_manager/test_def204_round2_ceiling.py 2>/dev/null && echo "EXISTS" || echo "ABSENT (will create)"
     ```

## Constraints

- Do NOT modify:
  - `argus/execution/order_manager.py::reconstruct_from_broker` BODY beyond the single-line `is_reconstructed = True` addition + the AC3.6 initialization fix (per AC3.7 + SbC §"Do NOT modify" #5). A-class halt A12 fires on broader edits.
  - `argus/main.py::check_startup_position_invariant`, `_startup_flatten_disabled`, the `reconstruct_from_broker()` call site (~line 1081 directional). SbC §"Do NOT modify" #5 / A-class halt A12.
  - `argus/execution/order_manager.py` DEF-199 A1 fix region (regression invariant 1).
  - `argus/execution/order_manager.py` DEF-158 3-branch side-check inside `_check_flatten_pending_timeouts` (regression invariant 8 / A-class halt A5).
  - `argus/execution/ibkr_broker.py::place_bracket_order` OCA threading — DEC-386 S1a (regression invariant 6).
  - `argus/execution/ibkr_broker.py::_handle_oca_already_filled` — DEC-386 S1b.
  - `argus/execution/ibkr_broker.py::_is_oca_already_filled_error` — relocation deferred to Sprint 31.93.
  - The Path #2 implementation from S3b (`_is_locate_rejection`, `_is_locate_suppressed`, `_handle_suppression_timeout_for_position`, `_read_positions_post_refresh`, the 4 emit-site exception handlers, the AC2.5 fallback). S4a-i layers the ceiling guard ON TOP of S3b's locate-suppression logic at the same emit sites — additive only.
  - The DEC-385 `phantom_short_retry_blocked` SystemAlertEvent emitter source — preserved verbatim (regression invariant 5).
  - The frontend (`frontend/`, `argus/ui/`) — zero UI scope (regression invariant 12 / B-class halt B8).
  - The `workflow/` submodule (RULE-018).
  - SimulatedBroker semantic behavior (SbC §"Do NOT modify" #2 / SbC §"Out of Scope" #18).

- Do NOT change:
  - DEC-117 atomic-bracket invariants (regression invariant 1 / A-class halt A10).
  - DEC-369 broker-confirmed reconciliation immunity — AC3.6 + AC3.7 compose ADDITIVELY with DEC-369 (BOTH protections apply); do NOT remove DEC-369's protection (regression invariant 3 / A-class halt A8).
  - DEC-372 stop retry caps + backoff (regression invariant 4).
  - DEC-388 alert observability — only the 14th `sell_ceiling_violation` entry is added; existing 13 unchanged (regression invariant 7).
  - The `# OCA-EXEMPT:` exemption mechanism (regression invariant 9).

- Do NOT add:
  - A new "warn-only" state to `_check_sell_ceiling` — booleans only per AC3.8 / SbC §"Edge Cases to Reject" #7.
  - Cross-position SELL aggregation on the same symbol — per-`ManagedPosition` only per AC3.4 / SbC §"Edge Cases to Reject" #8.
  - Ceiling check at `place_bracket_order` — bracket placement is EXPLICITLY EXCLUDED per AC3.2 / SbC §"Edge Cases to Reject" #15.
  - SQLite persistence for `cumulative_pending_sell_shares`, `cumulative_sold_shares`, or `is_reconstructed` — DEF-209 deferred to Sprint 35+ Learning Loop V2.
  - A second alert type beyond `sell_ceiling_violation` — only one POLICY_TABLE entry added (regression invariant 7 / SbC §"Out of Scope" #13).
  - Ceiling guard at the remaining 4 standalone-SELL emit sites — those land at S5b composite per session-breakdown.

- Do NOT cross-reference other session prompts. This prompt is standalone.

## Operator Choice (N/A this session)

S4a-i does not require operator pre-check. The atomic-method shape is committed via H-R2-1; auto-activation is committed via Decision 4.

## Canary Tests

Before making any changes, run the canary-test skill in `.claude/skills/canary-test.md` with these tests to confirm baseline behavior:

- `tests/api/test_policy_table_exhaustiveness.py::test_policy_table_count_matches_expected` (or equivalent — 13 entries pre-S4a-i).
- The S3b regression tests (`test_locate_rejection_triggers_suppression_at_*`, `test_branch_4_throttle_one_per_hour_per_position`, etc.) — confirms S3b baseline holds before S4a-i layers the ceiling guard on top.
- `argus/execution/order_manager.py::on_fill` test for SELL fills — confirms the existing fill handler before pending/sold transfer logic is added.
- DEC-369 broker-confirmed-reconciliation immunity test — A-class halt A8 baseline.

These set the "before" baseline for the after-implementation regression check.

## Test Targets

After implementation:

- Existing tests: all must still pass. Pytest baseline ≥ 5,278 (post-S3b; regression invariant 10 / B-class halt B3). Vitest unchanged at 913 (regression invariant 12).
- New tests in `tests/execution/order_manager/test_def204_round2_ceiling.py` (NEW FILE — 7 effective tests per session-breakdown.md lines 979–986):

  1. `test_cumulative_pending_increments_synchronously_before_await` (AC3.1 / state transition #1) — call `_reserve_pending_or_fail`; assert `position.cumulative_pending_sell_shares` increments synchronously (the test inspects state mid-call via mocked-time injection or post-call read; the assertion is that the increment is observable BEFORE any `await place_order` happens). **AST scan companion:** `test_no_await_in_reserve_pending_or_fail_body` walks `ast.parse(textwrap.dedent(inspect.getsource(om._reserve_pending_or_fail)))` for `ast.Await` nodes; assertion fails on any await.

  2. `test_cumulative_pending_decrements_on_cancel_reject` (AC3.1 / state transitions #2 + #3) — parametrized × 2: cancel path and reject path. Spawn position; reserve pending qty=10; trigger `on_cancel` (or `on_reject`) with that order; assert `cumulative_pending_sell_shares` decremented to 0.

  3. `test_cumulative_pending_transfers_to_sold_on_partial_fill` (AC3.1 / state transition #4) — spawn position with `pending=10, sold=0, total=100`; trigger `on_fill` with `filled_qty=4`; assert post-state `pending=6, sold=4, total=100` (synchronous transfer, no torn intermediate state observable).

  4. `test_cumulative_pending_transfers_to_sold_on_full_fill` (AC3.1 / state transition #5) — same pattern, `filled_qty=10`; assert post-state `pending=0, sold=10`.

  5. `test_concurrent_sell_emit_race_blocked_by_pending_reservation` — **CANONICAL C-1 RACE TEST** (AC3.5 / regression invariant 13): two coroutines on same `ManagedPosition` with `total=10` both attempt SELL emission with `requested=8` (sum=16 > total). First coroutine calls `_reserve_pending_or_fail(position, 8)` → True; pending now 8. Second coroutine calls `_reserve_pending_or_fail(position, 8)` → False (because `pending(8) + sold(0) + requested(8) = 16 > 10`); refuses SELL. Assert: only ONE coroutine's `place_order` is observed by the mock broker; the other's path emits `sell_ceiling_violation`.

  6. `test_check_sell_ceiling_blocks_excess_sell_at_canonical_trail_flatten_site` — single-site per session-breakdown's option-δ-prime mitigation. Mock the broker; spawn position with `total=10, sold=8, pending=0`; invoke `_trail_flatten` with `requested=5` (would push to 13 > 10); assert `sell_ceiling_violation` SystemAlertEvent emitted with the expected metadata `{position_id, symbol, requested_qty=5, pending=0, sold=8, shares_total=10, emit_site="_trail_flatten"}`; assert NO `place_order` call observed; assert pending counter NOT incremented (the failed reserve does not leak).

  7. `test_pending_sell_age_watchdog_auto_activates_on_first_case_a_in_production` (AC2.7 + Decision 4 / regression invariant 26) — spawn position; preload `_locate_suppressed_until[position.id]` (S3b state) AND set `last_sell_emit_time` such that the synthetic `case_a_in_production` event fires; call `_maybe_auto_activate_watchdog`; assert `self._watchdog_enabled_state` flipped from `"auto"` to `"enabled"`; assert structured log line `event="watchdog_auto_to_enabled"` was emitted with `case_a_evidence` payload. Idempotency check: call `_maybe_auto_activate_watchdog` a second time with a different position; assert state remains `"enabled"` (re-entrant flips are no-ops per H-R3-2).

- POLICY_TABLE exhaustiveness regression guard: existing `tests/api/test_policy_table_exhaustiveness.py` updated; the count assertion goes from 13 → 14, and a new assertion verifies `sell_ceiling_violation` is present in the table with `operator_ack_required=True` and `auto_resolution_predicate=None`.

- Test command (scoped per DEC-328, non-final session):

  ```
  python -m pytest tests/execution/order_manager/ tests/api/test_policy_table_exhaustiveness.py -n auto -q
  ```

## Config Validation

S4a-i consumes config fields established at S3a (`long_only_sell_ceiling_enabled`, `pending_sell_age_watchdog_enabled`); it does not add new ones. Verify during pre-flight that the S3a Pydantic model exists and the YAML field names match exactly. If S3a established the config validation tests, those should already cover these fields.

| YAML Key | Model Field |
|----------|-------------|
| `order_manager.long_only_sell_ceiling_enabled` | `OrderManagerConfig.long_only_sell_ceiling_enabled` |
| `order_manager.long_only_sell_ceiling_alert_on_violation` | `OrderManagerConfig.long_only_sell_ceiling_alert_on_violation` |
| `order_management.pending_sell_age_watchdog_enabled` | `OrderManagerConfig.pending_sell_age_watchdog_enabled` |

## Marker Validation (N/A — no new pytest markers)

S4a-i does not add pytest markers.

## Risky Batch Edit — Staged Flow

S4a-i's diff in `order_manager.py` is moderate (3 fields + 2 new methods + 4 callback-path edits + 1 emit-site guard + 1 reconstruct-line + 1 init-state + 1 auto-flip method) — this fits the staged flow per RULE-039:

1. **Read-only exploration.** Walk `ManagedPosition`, `on_fill`, `on_cancel`, `on_reject`, `_trail_flatten`, `reconstruct_from_broker`, and the watchdog scaffolding (S3a-introduced).
2. **Findings report.** Enumerate: (a) whether `halt_entry_until_operator_ack` is already present (S3b ownership); (b) whether `is_reconstructed` is already present (S3b forward-compat allowance); (c) the exact shape of `on_fill`/`on_cancel`/`on_reject` to identify safe insertion points; (d) the watchdog scaffolding from S3a — what's already wired vs. what S4a-i introduces; (e) any deviations from the prompt-cited paths under RULE-038.
3. **Write the report.** Brief; commit only if it adds value.
4. **Halt.** Surface to operator + reviewer. Wait for confirmation. If `halt_entry_until_operator_ack` is missing (S3b didn't add it), include it in S4a-i's field-set (4 fields total) and disclose the merge.
5. **Apply edits exactly as listed.** No drive-by improvements per RULE-007.

If the watchdog scaffolding is fundamentally absent at S3a (e.g., `_pending_sell_age_seconds` config field exists but no detection path is wired), document the auto-activation as deferred to S5b composite OR halt for operator disposition — building the entire watchdog detection path at S4a-i would push compaction over 13.5.

## Visual Review (N/A — backend-only)

S4a-i is backend-only. Zero UI changes (regression invariant 12).

## Definition of Done

- [ ] `ManagedPosition` has 3 new fields (`cumulative_pending_sell_shares`, `cumulative_sold_shares`, `is_reconstructed`); the 4th (`halt_entry_until_operator_ack`) verified present from S3b.
- [ ] `_reserve_pending_or_fail()` synchronous atomic method landed; AST guard test passes; mocked-await injection test passes.
- [ ] `_check_sell_ceiling()` thin-wrapper helper landed.
- [ ] State transitions #2 (cancel), #3 (reject), #4 (partial-fill), #5 (full-fill) wired in `on_cancel`, `on_reject`, `on_fill`.
- [ ] `_trail_flatten` canonical emit-site guarded with `_reserve_pending_or_fail` + `sell_ceiling_violation` alert emission. (Remaining 4 emit sites land at S5b composite.)
- [ ] `reconstruct_from_broker` sets `is_reconstructed = True`; AC3.6 initialization verified (zero counters + `shares_total = abs(broker_position.shares)`).
- [ ] `_maybe_auto_activate_watchdog` method landed; auto-flip from `"auto"` → `"enabled"` is asyncio.Lock-guarded, idempotent, and emits `event="watchdog_auto_to_enabled"` structured log line per H-R3-2.
- [ ] `sell_ceiling_violation` POLICY_TABLE 14th entry; `operator_ack_required=True`, `auto_resolution_predicate=None`.
- [ ] AST exhaustiveness regression guard updated 13 → 14 entries; `sell_ceiling_violation` key presence asserted.
- [ ] All 7 effective new tests passing.
- [ ] All existing pytest still passing.
- [ ] Pre-existing flake count unchanged (regression invariant 11 / B-class halt B1).
- [ ] CI green per RULE-050.
- [ ] Close-out report written to file (DEC-330).
- [ ] Tier 2 review completed via @reviewer subagent.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| `git diff HEAD~1 -- argus/execution/order_manager.py` shows zero edits to DEF-199 A1 fix region | Manual diff inspection (regression invariant 1) |
| `git diff HEAD~1 -- argus/execution/order_manager.py` shows zero edits to DEF-158 3-branch side-check region | Manual diff inspection (regression invariant 8 / A-class halt A5) |
| `git diff HEAD~1 -- argus/execution/order_manager.py::reconstruct_from_broker` shows ONLY the single-line `is_reconstructed = True` addition + (if needed) AC3.6 zero-counter initialization | Manual diff inspection (A-class halt A12 boundary) |
| `git diff HEAD~1 -- argus/main.py` returns empty | A-class halt A12 |
| `git diff HEAD~1 -- argus/execution/ibkr_broker.py` returns empty | Out-of-scope at S4a-i |
| `git diff HEAD~1 -- argus/models/trading.py` returns empty | Existing baseline |
| `git diff HEAD~1 -- frontend/` AND `argus/ui/` returns empty | Regression invariant 12 / B-class halt B8 |
| `python -c "import ast, inspect; from argus.execution.order_manager import OrderManager; src = inspect.getsource(OrderManager._reserve_pending_or_fail); tree = ast.parse(src); awaits = [n for n in ast.walk(tree) if isinstance(n, ast.Await)]; print(len(awaits))"` returns `0` | AST guard / FAI #1 / regression invariant 23 baseline |
| `grep -n "cumulative_pending_sell_shares\|cumulative_sold_shares\|is_reconstructed" argus/execution/order_manager.py | wc -l` ≥ 8 | Field declarations + usages |
| `grep -nE "long_only_sell_ceiling_enabled" argus/execution/order_manager.py` ≥ 1 hit | AC3.8 config-gate present |
| `grep -n "sell_ceiling_violation" argus/core/alert_auto_resolution.py` returns 1 hit | POLICY_TABLE entry present (regression invariant 7) |
| Test `test_policy_table_exhaustiveness` count assertion is 14, not 13 | AC3.9 / regression invariant 7 |
| Test count delta from S3b baseline ≥ +7 (new tests in `test_def204_round2_ceiling.py`) | Close-out reports actual delta |
| Pre-existing flake count unchanged | DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/session-s4a-i-closeout.md
```

Do NOT just print the report in the terminal. Create the file, write the full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.92-def-204-round-2/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.92-def-204-round-2/session-s4a-i-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/execution/order_manager/ tests/api/test_policy_table_exhaustiveness.py -n auto -q` (scoped per DEC-328; non-final session).
5. Files that should NOT have been modified:
   - `argus/main.py`
   - `argus/execution/order_manager.py::reconstruct_from_broker` BODY beyond single-line `is_reconstructed = True` + AC3.6 initialization fix
   - `argus/execution/order_manager.py` DEF-158 3-branch side-check region
   - `argus/execution/order_manager.py` DEF-199 A1 fix region
   - `argus/execution/ibkr_broker.py` (any modification)
   - `argus/execution/simulated_broker.py`
   - `argus/models/trading.py`
   - `argus/execution/alpaca_broker.py`
   - `argus/data/alpaca_data_service.py`
   - `frontend/`, `argus/ui/`
   - `workflow/` submodule

The @reviewer will produce its review report at:

```
docs/sprints/sprint-31.92-def-204-round-2/session-s4a-i-review.md
```

The verdict JSON is fenced with ` ```json:structured-verdict `.

## Post-Review Fix Documentation

Same pattern as the implementation-prompt template — see template §"Post-Review Fix Documentation". If @reviewer reports CONCERNS and the findings are fixed within this session, append "Post-Review Fixes" to `session-s4a-i-closeout.md` and "Post-Review Resolution" to `session-s4a-i-review.md`. Update the verdict JSON to `CONCERNS_RESOLVED`. ESCALATE findings must NOT be fixed without human review.

## Session-Specific Review Focus (for @reviewer)

1. **Synchronous-update invariant on the place-time path.** Verify `_reserve_pending_or_fail`'s body is synchronous from the read of `cumulative_pending_sell_shares` to the write of the increment. The AST guard test (`test_no_await_in_reserve_pending_or_fail_body`) is the structural defense; verify it's present and exercises `ast.parse + ast.walk` on the actual implementation source, not a mocked stand-in. The mocked-await injection companion test is what makes the guard sound — without injection, the guard could be passing for the wrong reason.

2. **Field-ownership clarity (S3b vs S4a-i).** Verify `halt_entry_until_operator_ack` is added EXACTLY ONCE — either at S3b (per S3b's prompt) or at S4a-i (if S3b didn't land it). If both sessions add it, that's a merge conflict; if neither adds it, that's a missing field. The close-out's "field-ownership disclosure" should explicitly state which session added each of the 4 new fields.

3. **AC3.7 `is_reconstructed` refusal short-circuit position.** In `_reserve_pending_or_fail`, the `is_reconstructed` check MUST occur BEFORE the counter math. If a reconstructed position with `pending=0, sold=0, total=10, requested=5` reaches `_reserve_pending_or_fail`, the method returns False — NOT True (the math would technically allow). This short-circuit is the structural defense per regression invariant 19; verify it's wired correctly.

4. **AC3.6 broker-confirmed initialization composes additively with DEC-369.** A-class halt A8 — verify `reconstruct_from_broker`-derived positions:
   - Initialize `cumulative_pending_sell_shares = 0` (dataclass default suffices).
   - Initialize `cumulative_sold_shares = 0` (dataclass default suffices).
   - Set `is_reconstructed = True` (the single-line addition).
   - Have `shares_total = abs(broker_position.shares)` (existing initialization preserved).
   - DEC-369 reconciliation immunity is NOT removed — both protections apply.

5. **AC2.7 watchdog auto-activation atomicity.** Verify:
   - `self._watchdog_state_lock` is `asyncio.Lock`, not `threading.Lock`.
   - The flip is guarded by `async with self._watchdog_state_lock:`.
   - Re-entrant flips are no-ops (the inside-lock check `if self._watchdog_enabled_state != "auto": return` covers this).
   - The structured log line uses `extra={"event": "watchdog_auto_to_enabled", "case_a_evidence": {...}}` shape (operator-visible) per H-R3-2.
   - Restart resets to `"auto"` — the field is in-memory only, not persisted (verify by inspecting `__init__` initialization vs SQLite/file load).

6. **POLICY_TABLE 14th entry shape.** Verify the `sell_ceiling_violation` entry uses `operator_ack_required=True` and `auto_resolution_predicate=None` (NEVER_AUTO_RESOLVE). The DEF-219 AST exhaustiveness regression guard is the structural defense; verify it's updated 13 → 14 AND additionally asserts the new key's presence.

7. **C-1 race test soundness.** Test 5 (`test_concurrent_sell_emit_race_blocked_by_pending_reservation`) is the canonical race test for AC3.5. Verify the test:
   - Actually exercises two coroutines on the SAME `ManagedPosition`.
   - The second coroutine's `_reserve_pending_or_fail` call sees the first's reservation (proves the synchronous-update invariant works for the protected path).
   - The mocked broker observes ONLY ONE `place_order` invocation.
   - The second coroutine's path emits `sell_ceiling_violation`.

8. **Bracket placement is NOT ceiling-checked.** Per AC3.2 + SbC §"Edge Cases to Reject" #15. Verify that `place_bracket_order` (or whatever the bracket-placement entry point is named) does NOT call `_reserve_pending_or_fail` or `_check_sell_ceiling`. Bracket-children placement is governed by DEC-117 atomicity, not by the per-emit ceiling.

9. **Watchdog auto-activation idempotency.** Verify the second `case_a_in_production` event does NOT re-flip or re-emit the structured log line. Test 7's idempotency check is the structural defense.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`.

Of particular relevance to S4a-i (✓-mandatory at S4a-i per the Per-Session Verification Matrix):

- **Invariant 1 (DEC-117 atomic bracket):** PASS — bracket placement explicitly excluded from ceiling check (AC3.2). A-class halt A10 fires on regression.
- **Invariant 3 (DEC-369 broker-confirmed immunity):** PASS — composes additively with `is_reconstructed=True` per AC3.6 / regression invariant 19. A-class halt A8 fires if conflict observed.
- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** PASS — `phantom_short_retry_blocked` emitter unchanged.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** PASS — bracket OCA threading unchanged at S4a-i.
- **Invariant 7 (DEC-388 alert observability):** ESTABLISHES — POLICY_TABLE 14th entry + AST exhaustiveness regression guard updated.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** PASS — any new SELL-related logic must use OCA threading or carry `# OCA-EXEMPT:` comment.
- **Invariant 10, 11, 12:** PASS — test count ≥ baseline (S3b + ~7 new); pre-existing flake count unchanged; frontend immutable.
- **Invariant 13 (SELL-volume ceiling pending+sold pattern):** ESTABLISHES — canonical site at `_trail_flatten` lands at S4a-i; remaining 4 sites at S5b.
- **Invariant 19 (`is_reconstructed` refusal posture):** ESTABLISHES — field added; `_reserve_pending_or_fail` + `_check_sell_ceiling` short-circuit on `is_reconstructed=True`. Refusal-posture regression test for ALL 4 standalone-SELL paths lives at S5b.
- **Invariant 20 (Pending-reservation state transitions):** ESTABLISHES — all 5 state transitions wired (place-time, cancel, reject, partial-fill, full-fill).
- **Invariant 26 (AC2.7 watchdog auto-activation):** ESTABLISHES — auto-flip from `auto` to `enabled` on first `case_a_in_production`; in-memory only, asyncio.Lock-guarded, idempotent, logged.

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`.

### A. Mandatory Halts (Tier 3 architectural review automatically fires)

Of particular relevance to S4a-i:

- **A6** (Tier 2 review verdict CONCERNS or ESCALATE). Halt; iterate within session for CONCERNS; operator decides for ESCALATE.
- **A8** (AC4 ceiling implementation reveals architectural conflict with DEC-369 broker-confirmed reconciliation immunity). Halt at mid-implementation. Tier 3 evaluates whether (a) compose additively (default per AC3.6 + AC3.7), (b) defer ceiling on broker-confirmed positions (rejected at Round 1 C-2), (c) third option.
- **A10** (chosen mechanism breaks DEC-117 atomic-bracket invariants). Halt; revert; escalate.
- **A11** (AC3 SELL-volume ceiling false-positive in production paper trading). Halt post-merge if observed. Specifically watch for: (a) fill-callback ordering or partial-fill aggregation defect; (b) pending counter not decremented on cancel/reject; (c) C-1 race fires unexpectedly; (d) callback-path leak (S4a-ii's regression infrastructure is the structural defense — if missing, A11 routes to S4a-ii diagnostic).
- **A12** (any session's diff touches `argus/main.py::check_startup_position_invariant`, `_startup_flatten_disabled`, the `reconstruct_from_broker()` call site, OR `reconstruct_from_broker` BODY beyond the single-line addition). Halt. The single-line `is_reconstructed = True` + AC3.6 zero-counter initialization is the EXCEPTION; any other change in S4a-i fires A12.
- **A14** (Round 3 verdict produces ≥1 Critical finding). Decision 7 routing applies; already invoked operator override per `escalation-criteria.md` § Round 3 Operator Override Log Entry.
- **A15** (restart-during-active-position regression test fails OR production paper-session reveals an ARGUS-emitted SELL on `is_reconstructed=True` position). The refusal-posture test at S5b is the test surface; if the field isn't correctly set or the short-circuit fails, A15 fires.
- **A16** (`is_reconstructed = True` refusal posture creates operationally undesirable failure mode in production — i.e., reconstructed position can't be flattened by ARGUS AND operator-manual flatten fails). Sprint-pause; Tier 3.
- **A19** (NEW per Decision 4 — informational, NOT halt): AC2.7 watchdog auto-activates from `auto` to `enabled` in production. **Informational logging event only.** Recorded as structured INFO log line + sprint-close pre-live transition checklist entry.

### B. Mandatory Halts (Tier 3 not required; operator + Tier 2 reviewer disposition)

- **B1** (pre-existing flake count increases). Per RULE-041, file DEF entry on first observation.
- **B3** (pytest baseline drops below ≥ S3b baseline). Halt; investigate.
- **B4** (CI fails on session's final commit AND failure is NOT a documented pre-existing flake). Halt per RULE-050.
- **B5** (structural anchor referenced in impl prompt does not match repo state during pre-flight). Re-anchor against actual structural anchors. Disclose under RULE-038.
- **B6** (a do-not-modify-list file appears in `git diff`). Revert.
- **B7** (test runtime degrades >2× from baseline OR a single test exceeds 60s). The new tests should be sub-second; if the C-1 race test exceeds 5s, mock the propagation path more aggressively.
- **B8** (frontend modification — zero scope). Revert.

### C. Soft Halts (Continue with extra caution + close-out flag)

- **C1** (out-of-scope improvements). Document in close-out under "Deferred Items"; do NOT fix in this session.
- **C5** (uncertain whether a change crosses do-not-modify boundary — e.g., a refactor near `reconstruct_from_broker` BODY). Pause; consult SbC; escalate to operator before making the change.
- **C6** (line numbers drift 1–5 from spec). Continue; document actual line numbers in close-out for next session's reference.
- **C9** (AC3.4 "per-managed-position ceiling" test deferred to S5b reveals two ManagedPositions on same symbol DO interact). If the interaction surfaces unexpectedly at S4a-i (e.g., during the C-1 race test), halt; investigate; file DEF if pre-existing OrderManager bug; otherwise fix at S4a-i or escalate.

---

*End Sprint 31.92 Session S4a-i implementation prompt.*
