# Sprint 31.92, Session S3b: Path #2 Wire-up + AC2.5 Refresh-Then-Verify + Branch 4 + C-R2-1↔H-R2-2 Coupling per Tier 3 item C + Fix A Single-Flight Serialization at IBKRBroker.refresh_positions() per Round 3 C-R3-1

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt. RULE-038 (grep-verify discipline), RULE-042 (`getattr` silent-default anti-pattern), RULE-043 (`except Exception:` swallowing test signals), RULE-044/045 (timezone-sensitive tests), and RULE-050 (CI-green discipline) apply with particular force.

2. Read these files to load context:
   - `argus/execution/order_manager.py` — specifically the four standalone-SELL exception handlers (`_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts`, `_escalation_update_stop`) and the housekeeping loop in `_check_flatten_pending_timeouts` where the suppression-timeout fallback lives. Anchor by function names (line numbers DIRECTIONAL ONLY per protocol v1.2.0+).
   - `argus/execution/broker.py` — abstract `Broker` class (the only ABC modification permitted in this sprint per SbC §"Do NOT modify" #2).
   - `argus/execution/ibkr_broker.py` — current `IBKRBroker` impl. Note `_is_oca_already_filled_error` helper as the canonical pattern reference for `_is_locate_rejection` (per AC2.1 / DEC-386 S1b).
   - `argus/execution/simulated_broker.py` — `SimulatedBroker.place_order` and surrounding context.
   - `argus/core/risk_manager.py` — existing Check 0 (DEC-027) — H-R3-3 extends Check 0 to reject entries on positions with `halt_entry_until_operator_ack=True`.
   - `argus/core/events.py::SystemAlertEvent` schema — DEC-385 L2 metadata field; preserved verbatim per regression invariant 5.
   - `docs/decision-log.md::DEC-385` — the `phantom_short_retry_blocked` alert path is reused conditionally per AC2.5 case (c) AND Branch 4 (`verification_stale: true`); the emitter itself is preserved verbatim.
   - The S3a close-out artifact (helper signatures `_is_locate_rejection`, `_is_locate_suppressed`, dict-key semantics, config field defaults). Anchor: `docs/sprints/sprint-31.92-def-204-round-2/session-s3a-closeout.md` (or whatever S3a actually wrote — grep-verify the filename if not present at expected path).
   - The Round 3 disposition Fix A description: `docs/sprints/sprint-31.92-def-204-round-2/round-3-disposition.md` § 2.1 (C-R3-1 disposition) + § 5.1 (RSK-REFRESH-POSITIONS-CONCURRENT-CALLER).
   - The pending FAI #10 text: `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md` § "Pending FAI extensions committed in `round-3-disposition.md`" → "Pending FAI #10".

3. Run the test baseline (DEC-328 — Session 5+ of sprint, scoped):

   ```
   python -m pytest tests/execution/order_manager/ tests/execution/test_ibkr_broker.py -n auto -q
   ```

   Expected: all passing (full suite was confirmed by S3a's close-out). Note: in autonomous mode, the expected test count is dynamically adjusted by the runner based on the previous session's actual results; the count above is the planning-time estimate.

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** from the "Files to Modify" section below. For each entry, run the verbatim grep-verify command and confirm the anchor still resolves to the expected location. If drift is detected, disclose under RULE-038 in the close-out and proceed against the actual structural anchors. If the anchor is not found at all, HALT and request operator disposition rather than guess.

6. Verify S3a's deliverables are present on `main`:

   ```bash
   grep -n "_is_locate_rejection" argus/execution/ibkr_broker.py
   grep -n "_is_locate_suppressed" argus/execution/order_manager.py
   grep -n "_locate_suppressed_until" argus/execution/order_manager.py
   grep -n "_LOCATE_REJECTED_FINGERPRINT" argus/execution/ibkr_broker.py
   grep -n "locate_suppression_seconds" argus/core/config.py
   grep -n "long_only_sell_ceiling_enabled" argus/core/config.py
   grep -n "pending_sell_age_watchdog_enabled" argus/core/config.py
   ```

   All seven must match. If any are missing, halt — S3a has not landed yet.

7. **Path-verification under RULE-038 — surface and resolve before editing:** the Round 3 disposition § 7.1 amendment manifest names two paths that diverge from current ARGUS structure. Run:

   ```bash
   ls argus/risk/ 2>/dev/null && echo "argus/risk/ EXISTS" || echo "argus/risk/ ABSENT"
   ls argus/api/v1/ 2>/dev/null && echo "argus/api/v1/ EXISTS" || echo "argus/api/v1/ ABSENT"
   ls argus/core/risk_manager.py && echo "argus/core/risk_manager.py PRESENT"
   ls argus/api/routes/ | head -3
   ```

   The risk manager is at `argus/core/risk_manager.py` (NOT `argus/risk/risk_manager.py`), and routes live under `argus/api/routes/` (NOT `argus/api/v1/`). The Round 3 disposition's path strings were aspirational; treat them as DIRECTIONAL ONLY per protocol v1.2.0+ and use the actual ARGUS layout (`argus/core/risk_manager.py` for the Check 0 extension; `argus/api/routes/positions.py` as a NEW file for the halt-clear endpoint). Disclose this drift in the close-out's RULE-038 section.

## Objective

Wire `_is_locate_rejection()` exception classification + `_is_locate_suppressed(position, now)` pre-check (both established at S3a) into all four standalone-SELL paths (`_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts`, `_escalation_update_stop`); implement the new `Broker.refresh_positions(timeout_seconds: float = 5.0)` ABC method (C-R2-1) plus AC2.5 broker-verified suppression-timeout fallback with three branches (zero / expected-long / unexpected) and Branch 4 (`verification_stale: true`) on refresh failure; enforce the C-R2-1↔H-R2-2 coupling per Tier 3 item C — if H1 is the active mechanism AND `Broker.refresh_positions()` raises or times out, mark the position `halt_entry_until_operator_ack=True`; PLUS Fix A single-flight serialization wrapper at `IBKRBroker.refresh_positions()` (`asyncio.Lock` + 250ms coalesce window) per Round 3 C-R3-1 disposition with FAI #10 falsifying spike (N=20 concurrent-caller regression test); PLUS M-R3-2 Branch 4 alert throttling (1-hour per-position cooldown); PLUS H-R3-3 RiskManager Check 0 extension + halt-clear REST endpoint + CLI tool; PLUS H-R3-1 `time.monotonic()` substitution at all suppression-timeout sites.

## Requirements

1. **Add `Broker.refresh_positions(timeout_seconds: float = 5.0) -> None` ABC method** in `argus/execution/broker.py`. This is the only ABC modification permitted in this sprint per SbC §"Do NOT modify" #2.

   ```python
   @abstractmethod
   async def refresh_positions(self, timeout_seconds: float = 5.0) -> None:
       """Force a synchronous refresh of the broker's position cache.

       Per C-R2-1: AC2.5's broker-verified suppression-timeout fallback
       requires fresh broker state before classifying broker-shows-zero
       vs broker-shows-expected-long vs broker-shows-unexpected. Without
       this method, the cache may be stale after a Gateway disconnect/
       reconnect window (FAI #2).

       Per Round 3 C-R3-1: implementations MUST serialize concurrent
       callers via single-flight pattern with a coalesce window (Fix A);
       relying on the underlying SDK's de-duplication is insufficient
       because the per-caller wait_for correlation is unverified. See
       FAI #10.

       Args:
           timeout_seconds: Hard timeout on the broker round-trip.
               Default 5.0s. Implementations raise asyncio.TimeoutError
               (or an equivalent) on expiry.

       Raises:
           asyncio.TimeoutError: timeout_seconds elapsed before the
               broker confirmed cache synchronization.
           Exception: any broker-side error during the refresh.
       """
   ```

   The default keyword + positional signature must remain backward-compatible — existing callers pass nothing and get the 5s default.

2. **Implement `IBKRBroker.refresh_positions` with Fix A single-flight serialization** in `argus/execution/ibkr_broker.py`. Per Round 3 C-R3-1:

   ```python
   # Class-level (or instance-level) state introduced for Fix A:
   #   self._refresh_positions_lock: asyncio.Lock — single-flight gate.
   #   self._last_refresh_synchronized_at: float | None — monotonic
   #       timestamp of the last completed broker round-trip; None
   #       before any successful refresh.
   #   _REFRESH_POSITIONS_COALESCE_WINDOW_SECONDS = 0.250 — module-level
   #       constant for the 250ms coalesce window per Round 3 C-R3-1.

   async def refresh_positions(self, timeout_seconds: float = 5.0) -> None:
       """Single-flight wrapper per Round 3 C-R3-1 / FAI #10.

       Concurrent callers serialize via self._refresh_positions_lock.
       A caller arriving within COALESCE_WINDOW seconds of the prior
       successful refresh's synchronization timestamp returns immediately
       (cache IS fresh per the prior caller's broker round-trip). Outside
       that window, the caller acquires the lock and performs its own
       synchronized round-trip via IB.reqPositions() +
       asyncio.wait_for(self._position_end_event.wait(), timeout=...).

       Note: time.monotonic() is the canonical clock for both the
       coalesce-window check AND the timestamp recording per H-R3-1.
       """
       now = time.monotonic()
       last = self._last_refresh_synchronized_at
       if last is not None and (now - last) < _REFRESH_POSITIONS_COALESCE_WINDOW_SECONDS:
           return  # Coalesce: prior caller's refresh is still fresh.

       async with self._refresh_positions_lock:
           # Re-check post-acquisition (another coroutine may have
           # synchronized while we were waiting for the lock):
           now2 = time.monotonic()
           last2 = self._last_refresh_synchronized_at
           if last2 is not None and (now2 - last2) < _REFRESH_POSITIONS_COALESCE_WINDOW_SECONDS:
               return

           self._position_end_event.clear()  # NEW asyncio.Event the impl
                                             # creates if not already
                                             # present; bound to ib_async's
                                             # positionEnd callback.
           self._ib.reqPositions()
           await asyncio.wait_for(
               self._position_end_event.wait(),
               timeout=timeout_seconds,
           )
           self._last_refresh_synchronized_at = time.monotonic()
   ```

   The `_position_end_event` Event must be initialized in `__init__` and bound to ib_async's `positionEnd` event callback. If the Event already exists with semantics compatible with this usage, reuse it; otherwise add it. Verify during pre-flight.

   The `_refresh_positions_lock` MUST be `asyncio.Lock`, NOT `threading.Lock` (this is single-event-loop serialization, not cross-thread). The 250ms coalesce-window constant lives at module scope as `_REFRESH_POSITIONS_COALESCE_WINDOW_SECONDS = 0.250` for grep-discoverability.

3. **Implement `SimulatedBroker.refresh_positions` as no-op or instant-success** in `argus/execution/simulated_broker.py`:

   ```python
   async def refresh_positions(self, timeout_seconds: float = 5.0) -> None:
       """SimulatedBroker holds in-memory state; no broker round-trip needed.

       Per SbC §"Out of Scope" #18: production SimulatedBroker is NOT
       modified semantically. The Branch-4 (refresh-failure) test path
       uses the SimulatedBrokerWithRefreshTimeout fixture from
       tests/integration/conftest_refresh_timeout.py (S5c — out of
       scope for S3b)."""
       return None
   ```

   No locking, no fixture-side state mutation. The fixture variant lives ONLY in test code (S5c).

4. **Wire `_is_locate_rejection()` exception classification + `_is_locate_suppressed()` pre-check into all four standalone-SELL paths.** In `argus/execution/order_manager.py`, anchor by function name (line numbers DIRECTIONAL ONLY):

   - `_flatten_position` exception handler around `await self._broker.place_order(...)`.
   - `_trail_flatten` exception handler around the SELL emission.
   - `_check_flatten_pending_timeouts` exception handler around the retry-SELL emission (preserves DEF-158 3-branch side-check verbatim per regression invariant 8).
   - `_escalation_update_stop` exception handler around the emergency-flatten SELL.

   At each site, wrap the SELL emission with:

   ```python
   # Pre-emit suppression check (AC2.4)
   now_mono = time.monotonic()
   if self._is_locate_suppressed(position, now_mono):
       logger.info(
           "SELL suppressed for position %s (locate-rejection within window)",
           position.id,
       )
       return  # Or branch-equivalent skip; do NOT call place_order.

   try:
       await self._broker.place_order(...)
   except Exception as exc:
       # Path #2 detection (AC2.3): classify exception.
       if _is_locate_rejection(exc):  # Helper from S3a in ibkr_broker.py
           self._locate_suppressed_until[position.id] = (
               time.monotonic()
               + self._config.locate_suppression_seconds
           )
           logger.warning(
               "Locate-rejection at %s for position %s: suppressing "
               "further SELLs for %ds",
               <site_name>,
               position.id,
               self._config.locate_suppression_seconds,
           )
           # OCA-EXEMPT: no OCA grouping on suppression-side handling
           # (no order placed); preserves DEC-386 OCA invariants.
           return
       raise  # Unmodeled exception class — preserve existing handling.
   ```

   **All four sites use `time.monotonic()`** per regression invariant 31 / Round 3 H-R3-1 — `time.time()` is wall-clock-skew-vulnerable and was empirically a flake source in DEF-150-class tests.

   **DEF-158 3-branch side-check (BUY/SELL/unknown) inside `_check_flatten_pending_timeouts` is preserved verbatim** per regression invariant 8 / SbC §"Edge Cases to Reject" #13. The Path #2 detection sits at the `place_order` exception in the retry-SELL emission; it does NOT add a 4th branch to the side-check. A-class halt A5 fires if violated.

5. **Implement AC2.5 broker-verified suppression-timeout fallback (three branches + Branch 4 + HALT-ENTRY coupling).** In `_check_flatten_pending_timeouts` housekeeping loop OR as a private method on `OrderManager` (do NOT add a new module per SbC §"Do NOT add"):

   ```python
   async def _read_positions_post_refresh(self) -> dict[str, Position]:
       """Helper per Round 3 M-R3-4: composes refresh_positions +
       get_positions into a single synchronous read-after-refresh
       sequence. The AST-no-await scan at S4a-ii (regression invariant
       30) asserts no ast.Await between refresh completion and cache
       read — the only ast.Await in this method body is the
       refresh_positions call itself.

       Performance budget per spec § Performance Benchmarks:
       ≤5µs per-call overhead exclusive of refresh round-trip.
       """
       await self._broker.refresh_positions(timeout_seconds=5.0)
       return self._broker.get_positions()

   async def _handle_suppression_timeout_for_position(
       self, position: ManagedPosition, now_mono: float
   ) -> None:
       """AC2.5 fallback. Branches 1/2/3 on refresh success;
       Branch 4 (verification_stale: true) on refresh failure.

       Branch 4 throttle per Round 3 M-R3-2: 1-hour per-position
       cooldown at alert layer; HALT-ENTRY effect persists.

       HALT-ENTRY coupling per Tier 3 item C / AC2.8: if H1 is the
       active mechanism (per S2a JSON output) AND refresh fails,
       mark position halt_entry_until_operator_ack=True.
       """
       try:
           broker_positions = await self._read_positions_post_refresh()
       except Exception as exc:
           # BRANCH 4: verification_stale.
           # Throttle per M-R3-2.
           last_branch4 = self._branch4_last_alert_at.get(position.id, 0.0)
           if now_mono - last_branch4 >= 3600.0:
               # First firing within 1-hour window — publish.
               self._branch4_last_alert_at[position.id] = now_mono
               await self._event_bus.publish(SystemAlertEvent(
                   alert_type="phantom_short_retry_blocked",
                   severity="critical",
                   metadata={
                       "verification_stale": True,
                       "verification_failure_reason": type(exc).__name__,
                       "position_id": position.id,
                       "symbol": position.symbol,
                   },
               ))
           else:
               logger.info(
                   "Branch 4 throttled for position %s "
                   "(branch_4_throttled: true)",
                   position.id,
               )

           # HALT-ENTRY coupling per Tier 3 item C / AC2.8.
           if self._selected_mechanism == "h1_cancel_and_await":
               position.halt_entry_until_operator_ack = True
               logger.warning(
                   "halt_entry_set for position %s (H1 + refresh fail)",
                   position.id,
                   extra={"event": "halt_entry_set", "position_id": position.id},
               )
           return

       # Refresh succeeded; classify per Branches 1/2/3.
       broker_pos = broker_positions.get(position.symbol)
       if broker_pos is None or broker_pos.shares == 0:
           # BRANCH 1: broker-zero. Held order resolved cleanly.
           logger.info("Suppression-timeout: broker shows zero for %s", position.symbol)
           self._locate_suppressed_until.pop(position.id, None)
           return

       if broker_pos.side == OrderSide.BUY and broker_pos.shares >= position.shares_remaining:
           # BRANCH 2: expected-long. No phantom short.
           logger.info(
               "Suppression-timeout: broker shows expected long for %s "
               "(shares=%d ≥ remaining=%d)",
               position.symbol, broker_pos.shares, position.shares_remaining,
           )
           self._locate_suppressed_until.pop(position.id, None)
           return

       # BRANCH 3: unexpected (short OR divergent qty OR unknown side).
       # Reuse DEC-385 phantom_short_retry_blocked emitter verbatim
       # (regression invariant 5).
       await self._event_bus.publish(SystemAlertEvent(
           alert_type="phantom_short_retry_blocked",
           severity="critical",
           metadata={
               "position_id": position.id,
               "symbol": position.symbol,
               "broker_side": broker_pos.side.value if broker_pos.side else "unknown",
               "broker_shares": broker_pos.shares,
               "expected_remaining": position.shares_remaining,
           },
       ))
       self._locate_suppressed_until.pop(position.id, None)
   ```

   The `_branch4_last_alert_at: dict[str, float]` (keyed by `ManagedPosition.id` ULID) is a NEW in-memory `OrderManager` field, initialized to `{}` in `__init__`. Throttle resets implicitly on `on_position_closed` (clear the dict entry) AND on successful refresh observation (clear via dict-pop on Branches 1/2/3). Add the corresponding clear in the `on_position_closed` path.

6. **Add `halt_entry_until_operator_ack: bool = False` to `ManagedPosition`** in `argus/execution/order_manager.py`. This field is set ONLY by `_handle_suppression_timeout_for_position` when H1 is the active mechanism AND Branch 4 fires; cleared ONLY by the operator-ack path (Requirement 8 below). Per AC2.8 and regression invariant 24:

   ```python
   @dataclass
   class ManagedPosition:
       # ... existing fields including is_reconstructed (S4a-i adds that
       # field; if S4a-i has not landed yet, ADD is_reconstructed: bool =
       # False here as forward-compat — S4a-i then becomes a no-op for
       # the field declaration, only adding the assignment in
       # reconstruct_from_broker. Verify S4a-i ordering during pre-flight.)
       halt_entry_until_operator_ack: bool = False  # Per AC2.8 / Tier 3 item C.
   ```

   **Note on field-add ordering:** Per session-breakdown, S4a-i adds `halt_entry_until_operator_ack` alongside `cumulative_pending_sell_shares`, `cumulative_sold_shares`, `is_reconstructed`. S3b precedes S4a-i in execution order. Add the field at S3b for the HALT-ENTRY coupling to compile and test; S4a-i then references the existing field rather than adding it. Disclose the field-ownership in S3b's close-out.

7. **Extend `RiskManager` Check 0 (existing DEC-027) to reject entries on positions with `halt_entry_until_operator_ack=True`** per H-R3-3 / regression invariant 32. In `argus/core/risk_manager.py`:

   ```python
   def _check0_halt_entry(
       self, signal: SignalEvent, managed_position: ManagedPosition | None
   ) -> RejectionReason | None:
       """Per AC2.8: if the entry signal targets a ManagedPosition.id
       that has halt_entry_until_operator_ack=True, reject. Per-position
       granularity preserved — new positions on the same symbol are
       NOT affected."""
       if managed_position is None:
           return None
       if managed_position.halt_entry_until_operator_ack:
           return RejectionReason(
               stage="risk_manager",
               reason="halt_entry_set",
               detail=(
                   f"Position {managed_position.id} is halted pending "
                   f"operator ack; clear via "
                   f"POST /api/v1/positions/{managed_position.id}/clear_halt "
                   f"or scripts/clear_position_halt.py."
               ),
           )
       return None
   ```

   The existing Check 0 must compose this new check. Wire it as the FIRST sub-check of Check 0 (operator-ack precedes ordinary risk gating). Verify the existing Check 0 surface during pre-flight — if it does not have the structure assumed here, adapt to the actual shape (RULE-038).

8. **Add halt-clear REST endpoint + CLI tool** per H-R3-3 / regression invariant 32. CREATE `argus/api/routes/positions.py` (NEW file, ~30 LOC):

   ```python
   from fastapi import APIRouter, Depends, HTTPException

   from argus.api.auth import require_auth
   from argus.api.dependencies import AppState, get_app_state

   router = APIRouter()

   @router.post("/api/v1/positions/{position_id}/clear_halt")
   async def clear_position_halt(
       position_id: str,
       state: AppState = Depends(get_app_state),
       _auth: dict = Depends(require_auth),
   ) -> dict:
       """Clear halt_entry_until_operator_ack on a managed position.

       Per AC2.8 / H-R3-3: operator-driven resolution for HALT-ENTRY
       posture under H1 + refresh failure. No automatic recovery."""
       om = state.order_manager
       if om is None:
           raise HTTPException(status_code=503, detail="OrderManager not initialized")
       position = om.find_managed_position(position_id)  # Verify the
                                                          # actual lookup
                                                          # method on OM.
       if position is None:
           raise HTTPException(status_code=404, detail=f"Position {position_id} not found")
       was_halted = position.halt_entry_until_operator_ack
       position.halt_entry_until_operator_ack = False
       logger.warning(
           "halt_entry_cleared for position %s (was_halted=%s)",
           position_id, was_halted,
           extra={
               "event": "halt_entry_cleared",
               "position_id": position_id,
               "was_halted": was_halted,
           },
       )
       return {"position_id": position_id, "was_halted": was_halted, "cleared": True}
   ```

   Wire `router` into `argus/api/routes/__init__.py` following the existing pattern (the canonical line-up of routers under `api_router`). Verify the existing wire-in pattern during pre-flight.

   CREATE `scripts/clear_position_halt.py` (NEW file, ~20 LOC):

   ```python
   """Operator CLI: clear halt_entry_until_operator_ack on a managed position.

   Usage: python scripts/clear_position_halt.py <position_id>

   Per AC2.8 / H-R3-3. Calls POST /api/v1/positions/{position_id}/clear_halt
   against the running ARGUS instance. Requires ARGUS_JWT_SECRET to be set.
   """
   import argparse, os, sys, urllib.request, json

   def main() -> int:
       parser = argparse.ArgumentParser()
       parser.add_argument("position_id")
       parser.add_argument("--host", default="localhost:8000")
       args = parser.parse_args()
       token = os.environ.get("ARGUS_OPERATOR_TOKEN")
       if not token:
           print("ARGUS_OPERATOR_TOKEN env var not set", file=sys.stderr)
           return 2
       req = urllib.request.Request(
           f"http://{args.host}/api/v1/positions/{args.position_id}/clear_halt",
           method="POST",
           headers={"Authorization": f"Bearer {token}"},
       )
       try:
           with urllib.request.urlopen(req) as resp:
               body = json.loads(resp.read())
               print(json.dumps(body, indent=2))
               return 0
       except urllib.error.HTTPError as e:
           print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
           return 1

   if __name__ == "__main__":
       sys.exit(main())
   ```

   Make executable: `chmod +x scripts/clear_position_halt.py` (record in close-out).

9. **`time.monotonic()` substitution at all suppression-timeout sites** per H-R3-1 / regression invariant 31. Replace `time.time()` with `time.monotonic()` at:
   - The 4 standalone-SELL exception handlers' `_locate_suppressed_until[position.id] = ...` writes (Requirement 4).
   - The AC2.5 timeout-check site inside `_check_flatten_pending_timeouts` housekeeping loop (the "is the suppression window expired?" check).
   - `_is_locate_suppressed(position, now)` callers — pass `now = time.monotonic()` everywhere; the helper itself was authored at S3a (verify it accepts a `now` parameter; if not, S3a's signature is `_is_locate_suppressed(position)` and now-injection should land here).

   The `OrderManagerConfig.locate_suppression_seconds` validator footnote per Round 3 H-R3-1 already notes "bounds (300–86400) are seconds in monotonic time per H-R3-1; equivalent to wall-clock under normal operation." Verify the docstring/footnote landed at S3a; if absent, append it here.

10. **Wire `selected_mechanism` runtime read into OrderManager.** The HALT-ENTRY coupling under H1 reads `self._selected_mechanism`. Source: S2a's JSON spike output written to `scripts/spike-results/spike-def204-round2-path1-results.json` and consumed at startup. The mechanism is stored on `OrderManager` at construction time:

    ```python
    self._selected_mechanism: str = bracket_oca_type_or_other_construction_path \
        # Source: read from S2a JSON during ArgusSystem.start() phase
        # construction; passed to OrderManager.__init__. If S2a has not
        # determined the mechanism, default to "h2_amend_stop_price" per
        # spec §"Hypothesis Prescription" PRIMARY DEFAULT.
    ```

    Verify the actual construction surface during pre-flight; if `selected_mechanism` is not yet a constructor parameter, add it as a keyword argument with default `"h2_amend_stop_price"` and pass it from `argus/main.py`'s OrderManager construction site (this is one of the few `argus/main.py` touches permitted at S3b — disclose in close-out under "Construction-surface modifications").

## Files to Modify

For each file the session edits, the structural anchor + edit shape + pre-flight grep-verify command are listed below. Line numbers MAY appear as directional cross-references but are NEVER the sole anchor — structural anchors bind per protocol v1.2.0+.

1. `argus/execution/broker.py`:
   - Anchor: abstract `class Broker(ABC):` definition; insert `refresh_positions` ABC method as a sibling of `cancel_all_orders`.
   - Edit shape: insertion of one new abstract async method.
   - Pre-flight grep-verify:
     ```bash
     grep -n "^class Broker" argus/execution/broker.py
     grep -n "cancel_all_orders" argus/execution/broker.py
     grep -n "@abstractmethod" argus/execution/broker.py | head -10
     # Expected: 1 hit on 'class Broker'; ≥1 hit on 'cancel_all_orders'.
     ```

2. `argus/execution/ibkr_broker.py`:
   - Anchor 1: function `_is_locate_rejection` (S3a-introduced) — verify presence.
   - Anchor 2: `IBKRBroker.__init__` — insert `self._refresh_positions_lock = asyncio.Lock()`, `self._last_refresh_synchronized_at: float | None = None`, and (if not present) `self._position_end_event = asyncio.Event()` plus the ib_async `positionEnd` callback wiring.
   - Anchor 3: insert `async def refresh_positions(self, timeout_seconds: float = 5.0) -> None:` method on `IBKRBroker` with Fix A body.
   - Anchor 4: module-level constant `_REFRESH_POSITIONS_COALESCE_WINDOW_SECONDS = 0.250`.
   - Edit shape: insertions only; no existing function bodies modified.
   - Pre-flight grep-verify:
     ```bash
     grep -n "_is_locate_rejection" argus/execution/ibkr_broker.py
     grep -n "class IBKRBroker" argus/execution/ibkr_broker.py
     grep -n "def __init__" argus/execution/ibkr_broker.py | head -3
     grep -n "_position_end_event\|positionEnd" argus/execution/ibkr_broker.py
     # Expected: ≥1 hit on _is_locate_rejection (S3a deliverable); 1 hit
     # on class IBKRBroker; ≥1 __init__. _position_end_event may or may
     # not be present.
     ```

3. `argus/execution/simulated_broker.py`:
   - Anchor: `class SimulatedBroker(Broker):`. Insert `async def refresh_positions(self, timeout_seconds: float = 5.0) -> None: return None`.
   - Edit shape: insertion of one new method (no-op body).
   - Pre-flight grep-verify:
     ```bash
     grep -n "^class SimulatedBroker" argus/execution/simulated_broker.py
     grep -n "async def cancel_all_orders\|async def place_order" argus/execution/simulated_broker.py
     ```

4. `argus/execution/order_manager.py`:
   - Anchor 1: function `_flatten_position` exception handler around `place_order` call site.
   - Anchor 2: function `_trail_flatten` exception handler around the SELL emission.
   - Anchor 3: function `_check_flatten_pending_timeouts` retry-SELL emission AND the housekeeping-loop suppression-timeout check site. **DEF-158 3-branch side-check structure preserved verbatim.**
   - Anchor 4: function `_escalation_update_stop` exception handler.
   - Anchor 5: `class ManagedPosition:` dataclass — add `halt_entry_until_operator_ack: bool = False` (and forward-compat `is_reconstructed: bool = False` if S4a-i has not landed).
   - Anchor 6: `OrderManager.__init__` — initialize `self._branch4_last_alert_at: dict[str, float] = {}` and `self._selected_mechanism: str = ...` (per Requirement 10).
   - Anchor 7: insertion point for new helpers `_handle_suppression_timeout_for_position` and `_read_positions_post_refresh` (private methods on `OrderManager`).
   - Anchor 8: `on_position_closed` close-path — add `self._branch4_last_alert_at.pop(position.id, None)` and `self._locate_suppressed_until.pop(position.id, None)` (the latter may already exist from S3a; verify).
   - Edit shape: 4 exception-handler insertions (Path #2 wire-up); 1 helper insertion; 1 dataclass field addition; 1 init-state addition; 1 close-path cleanup addition.
   - Pre-flight grep-verify:
     ```bash
     grep -n "def _flatten_position\|def _trail_flatten\|def _check_flatten_pending_timeouts\|def _escalation_update_stop" argus/execution/order_manager.py
     grep -n "class ManagedPosition" argus/execution/order_manager.py
     grep -n "_locate_suppressed_until" argus/execution/order_manager.py
     grep -n "DEF-158\|3-branch\|side-check" argus/execution/order_manager.py | head -5
     # Expected: 4 hits on the function defs; 1 hit on ManagedPosition;
     # ≥1 hit on _locate_suppressed_until (S3a deliverable);
     # multiple DEF-158 references (preserve verbatim).
     ```

5. `argus/core/risk_manager.py`:
   - Anchor: existing Check 0 (DEC-027) — extend to call new `_check0_halt_entry` first.
   - Edit shape: addition of one new sub-check method + integration into existing Check 0.
   - Pre-flight grep-verify:
     ```bash
     grep -n "Check 0\|DEC-027\|class RiskManager" argus/core/risk_manager.py
     grep -n "def evaluate_signal\|def _check0\|def _check_strategy_level" argus/core/risk_manager.py | head -5
     ```

6. `argus/api/routes/positions.py` (NEW FILE):
   - Anchor: file does not exist; CREATE.
   - Edit shape: new file ~30 LOC with `clear_position_halt` POST endpoint.
   - Pre-flight grep-verify:
     ```bash
     ls argus/api/routes/positions.py 2>/dev/null && echo "EXISTS" || echo "ABSENT (will create)"
     ```

7. `argus/api/routes/__init__.py`:
   - Anchor: existing `api_router = APIRouter()` aggregation pattern.
   - Edit shape: import the new positions router + include it.
   - Pre-flight grep-verify:
     ```bash
     grep -n "api_router\|include_router\|from .alerts\|from .health" argus/api/routes/__init__.py | head -10
     ```

8. `scripts/clear_position_halt.py` (NEW FILE):
   - Anchor: file does not exist; CREATE.
   - Edit shape: new ~20 LOC CLI tool.
   - Pre-flight grep-verify:
     ```bash
     ls scripts/clear_position_halt.py 2>/dev/null && echo "EXISTS" || echo "ABSENT (will create)"
     ```

9. `argus/main.py` (MINIMAL — construction-surface only):
   - Anchor: `OrderManager(...)` construction call site.
   - Edit shape: pass `selected_mechanism=...` keyword argument (read from S2a JSON or default to `"h2_amend_stop_price"`).
   - Pre-flight grep-verify:
     ```bash
     grep -n "OrderManager(" argus/main.py | head -5
     ```
   - **Constraint:** This is the ONLY `argus/main.py` modification permitted at S3b. Do NOT touch `check_startup_position_invariant`, `_startup_flatten_disabled`, the `reconstruct_from_broker()` call site (line ~1081 directional), or any phase-orchestration code. RULE-004 + SbC §"Do NOT modify" #5 apply. Disclose the construction-surface modification in close-out.

10. `tests/execution/order_manager/test_def204_round2_path2.py` (extend from S3a):
    - Anchor: existing test class structure from S3a.
    - Edit shape: append 8 new test functions (see Test Targets below).
    - Pre-flight grep-verify:
      ```bash
      ls tests/execution/order_manager/test_def204_round2_path2.py 2>/dev/null && echo "EXISTS"
      grep -n "def test_" tests/execution/order_manager/test_def204_round2_path2.py | wc -l
      ```

11. `tests/execution/test_ibkr_broker_concurrent_callers.py` (NEW FILE — FAI #10 falsifying spike):
    - Anchor: file does not exist; CREATE (~80 LOC, hard cap to avoid large-new-file compaction penalty).
    - Edit shape: new file containing N=20 concurrent-caller regression test.
    - Pre-flight grep-verify:
      ```bash
      ls tests/execution/test_ibkr_broker_concurrent_callers.py 2>/dev/null && echo "EXISTS" || echo "ABSENT (will create)"
      ```

## Constraints

- Do NOT modify:
  - `argus/execution/order_manager.py` DEF-199 A1 fix region (SbC §"Do NOT modify" — invariant 1 / A-class halt A12 surfaces).
  - `argus/execution/order_manager.py` DEF-158 3-branch side-check inside `_check_flatten_pending_timeouts` (BUY/SELL/unknown) — preserve verbatim per regression invariant 8 / SbC §"Edge Cases to Reject" #13. A-class halt A5 fires if a 4th branch is added.
  - `argus/execution/ibkr_broker.py` `place_bracket_order` OCA threading — DEC-386 S1a preserved byte-for-byte (regression invariant 6).
  - `argus/execution/ibkr_broker.py` `_handle_oca_already_filled` — DEC-386 S1b preserved verbatim.
  - `argus/execution/ibkr_broker.py` `_is_oca_already_filled_error` — relocation deferred to Sprint 31.93 (SbC §"Out of Scope" #4).
  - `argus/main.py::check_startup_position_invariant`, `_startup_flatten_disabled`, the `reconstruct_from_broker()` call site (~line 1081 directional), and surrounding phase-orchestration. SbC §"Do NOT modify" #5 + A-class halt A12.
  - `argus/execution/order_manager.py::reconstruct_from_broker` BODY — only the single-line `is_reconstructed = True` addition (per S4a-i AC3.7). Not in S3b's scope.
  - The DEC-385 `phantom_short_retry_blocked` SystemAlertEvent emitter source — reuse verbatim, conditional on AC2.5 case (c) + Branch 4.
  - The frontend (`frontend/`, `argus/ui/`) — zero UI scope (regression invariant 12 / B-class halt B8).
  - The `workflow/` submodule (RULE-018).
  - SimulatedBroker's existing fill-model semantics, immediate-fill behavior, OCA simulation — only ADD `refresh_positions` no-op (SbC §"Do NOT modify" #2 / SbC §"Out of Scope" #18).

- Do NOT change:
  - DEC-117 atomic-bracket invariants — A-class halt A10 fires.
  - DEC-364 `cancel_all_orders()` no-args ABC contract — backward-compat preserved (regression invariant 2).
  - DEC-369 broker-confirmed reconciliation immunity (regression invariant 3).
  - DEC-372 stop retry caps + backoff (regression invariant 4).
  - The `phantom_short_retry_blocked` POLICY_TABLE entry from DEC-388 — reuse the existing entry; Branch 4 metadata extends but does NOT replace (regression invariant 7). The `sell_ceiling_violation` 14th entry lands at S4a-i, NOT S3b.
  - The `# OCA-EXEMPT:` exemption mechanism (regression invariant 9).

- Do NOT add:
  - A new alert type beyond reusing `phantom_short_retry_blocked` for Branches 3 + 4. The `sell_ceiling_violation` entry is S4a-i's responsibility.
  - A new module under `argus/execution/` — the AC2.5 helpers live as private methods on `OrderManager`.
  - Threading-based locking — `asyncio.Lock` only.
  - A second config field for the Fix A coalesce window — the 250ms value is a module constant per Round 3 C-R3-1 (not config-tunable).
  - Production-side `SimulatedBrokerWithRefreshTimeout` — that fixture lives in test code only at S5c.

- Do NOT cross-reference other session prompts. This prompt is standalone.

## Operator Choice (N/A this session)

S3b does not require operator pre-check. Fix A serialization is committed in-sprint per Round 3 disposition § 1 (operator override invocation — already logged and binding).

## Canary Tests

Before making any changes, run the canary-test skill in `.claude/skills/canary-test.md` with these tests to confirm baseline behavior:

- The S3a-introduced helpers (`_is_locate_rejection`, `_is_locate_suppressed`) work in isolation.
- DEF-158 3-branch side-check tests in `tests/execution/order_manager/test_def204_session3_retry_side_check.py` (or whichever file owns DEF-158 regression) — confirms BUY/SELL/unknown semantics pre-S3b.
- DEC-386 OCA invariants test (`test_dec386_oca_invariants_preserved_byte_for_byte` if present) — confirms regression invariant 6 baseline.

These set the "before" baseline for the after-implementation regression check.

## Test Targets

After implementation:

- Existing tests: all must still pass. Pytest baseline ≥ 5,269 (regression invariant 10 / B-class halt B3).
- New tests in `tests/execution/order_manager/test_def204_round2_path2.py` (8 effective per session-breakdown.md lines 759–846):

  1. `test_locate_rejection_triggers_suppression_at_flatten_position` — mock IBKR to raise the locate-rejection exception inside `_flatten_position`; assert `_locate_suppressed_until[position.id]` is set; assert no SystemAlertEvent emitted at suppression-set time. (AC2.3)
  2. `test_locate_rejection_triggers_suppression_at_trail_flatten` — same shape at `_trail_flatten`.
  3. `test_locate_rejection_triggers_suppression_at_check_flatten_pending_timeouts` — same shape at the retry-SELL path; **assert DEF-158 3-branch side-check structure is unchanged** (BUY → resubmit / SELL → alert+halt / unknown → halt) — direct AST or grep regression.
  4. `test_locate_rejection_triggers_suppression_at_escalation_update_stop` — same shape at `_escalation_update_stop`.
  5. `test_subsequent_sell_skipped_during_suppression_at_canonical_site` — single-site canonical (per session-breakdown's parametrize × 1 mitigation; remaining 3 cases deferred to S5b composite). At `_trail_flatten`: spawn position; force locate-rejection at first SELL emit; second SELL emit attempt skipped via `_is_locate_suppressed` pre-check; no broker call observed.
  6. `test_suppression_timeout_broker_shows_zero_logs_info_no_alert` — AC2.5 Branch 1: refresh succeeds; broker shows no entry for symbol; INFO logged; dict entry cleared; no SystemAlertEvent.
  7. `test_suppression_timeout_broker_shows_expected_long_logs_info_no_alert` — AC2.5 Branch 2: refresh succeeds; broker shows BUY-side with shares ≥ remaining; INFO logged; dict entry cleared; no alert.
  8. `test_suppression_timeout_broker_shows_unexpected_state_emits_alert` — AC2.5 Branch 3: refresh succeeds; broker shows short OR divergent qty; assert `phantom_short_retry_blocked` published with metadata `{position_id, symbol, broker_side, broker_shares, expected_remaining}`; dict entry cleared.

- New tests for HALT-ENTRY + RiskManager + endpoint (4 tests, per regression invariants 24 + 32 + 34):

  9. `test_risk_manager_check0_rejects_when_halt_entry_set` — instantiate ManagedPosition with `halt_entry_until_operator_ack=True`; submit entry signal targeting that `ManagedPosition.id`; assert RiskManager rejects via Check 0 with `reason="halt_entry_set"`; submit entry signal targeting a DIFFERENT `ManagedPosition.id` on same symbol; assert NOT rejected (per-position granularity per AC2.8).
  10. `test_clear_halt_endpoint_requires_position_id_and_clears_flag` — call `POST /api/v1/positions/{id}/clear_halt` with valid + invalid IDs; valid clears the flag and emits `event="halt_entry_cleared"` log line; invalid returns 404. Use the `client` fixture from `tests/api/conftest.py`.
  11. `test_branch_4_throttle_one_per_hour_per_position` — fire Branch 4 (mock `refresh_positions` to raise) twice on same `ManagedPosition.id` within 1-hour window; first publishes `phantom_short_retry_blocked` with `verification_stale: true`; second is suppressed at alert layer (logged INFO with `branch_4_throttled: true`); HALT-ENTRY effect persists; advance synthetic clock past 1-hour window; third firing publishes alert again. (Regression invariant 34 / M-R3-2.)
  12. `test_locate_suppression_resilient_to_wall_clock_skew` — set up locate-suppression entry; inject a synthetic backwards wall-clock jump (simulate NTP correction) via `freeze_time` or equivalent; assert the suppression-timeout check uses `time.monotonic()` and is unaffected. **Implementation note:** assert `time.monotonic` is imported and `time.time` is NOT called inside the relevant code paths (grep regression on the diff). (Regression invariant 31 / H-R3-1.)

- New test in `tests/execution/test_ibkr_broker_concurrent_callers.py` (NEW FILE — FAI #10 falsifying spike):

  13. `test_concurrent_callers_serialized_by_single_flight_lock` — N=20 coroutines each call `IBKRBroker.refresh_positions()` near-simultaneously (≤10ms separation via `asyncio.gather`); inject a mocked-await delay between A's `reqPositions()` call and the `positionEnd` event firing; deterministically mutate broker state between A's and B's effective synchronization points. **Two modes:** (a) **Without mitigation** (monkey-patch the lock to a no-op): assert at least one caller observes stale-for-this-caller state (race observable). (b) **With mitigation enabled** (default code path): assert every caller observes fresh state (race NOT observable). The pair-wise comparison falsifies FAI #10 — the lock + coalesce-window pattern is what makes the race unobservable.

  Test fixture must inject the mocked-await between `IB.reqPositions()` invocation and the `positionEnd` event setter to simulate the per-caller correlation race. Use `pytest-asyncio` or `asyncio.run` per existing convention. **File hard-capped at ≤80 LOC** to avoid large-new-file compaction penalty per session-breakdown § Final mitigation.

- Test command (scoped per DEC-328, non-final session):

  ```
  python -m pytest tests/execution/order_manager/ tests/execution/test_ibkr_broker.py tests/execution/test_ibkr_broker_concurrent_callers.py -n auto -q
  ```

## Config Validation (N/A — no new YAML fields at S3b)

S3b consumes config fields established at S3a (`locate_suppression_seconds`, `pending_sell_age_watchdog_enabled`); it does not add new ones. The 250ms coalesce window is a module-level constant, not config-tunable (per Round 3 C-R3-1 design — operator-tuning the lock-window is not a supported scenario).

## Marker Validation (N/A — no new pytest markers)

S3b does not add pytest markers.

## Risky Batch Edit — Staged Flow

S3b touches 4 emit-site exception handlers + 5 production files + 3 NEW files + a test extension — moderate cross-file risk. Execute in five explicit phases per RULE-039:

1. **Read-only exploration.** Walk the 4 standalone-SELL emit sites in `order_manager.py`; read `_handle_oca_already_filled` for the pattern; read `_is_locate_rejection`/`_is_locate_suppressed` from S3a; trace the existing `selected_mechanism` plumbing (or absence thereof).
2. **Findings report.** In a scratch artifact (e.g., `docs/sprints/sprint-31.92-def-204-round-2/s3b-edit-plan.md` — this can be transient; commit only if it adds value), enumerate: (a) exact emit-site file:func locations and their existing `try/except` shape; (b) the actual structural anchor for `selected_mechanism` plumbing (constructor parameter? class attribute?); (c) the exact api/routes wiring pattern; (d) any deviations from the prompt-cited paths under RULE-038.
3. **Write the report.** Brief; sufficient for a fresh-context reviewer to verify the planned edits.
4. **Halt.** Surface the report to operator + reviewer. Wait for confirmation. If the plan reveals an unexpected structural drift (e.g., `selected_mechanism` would require `argus/main.py` modifications outside the construction-call-site scope), halt for explicit operator disposition.
5. **Apply edits exactly as listed.** No drive-by improvements. Scope discipline per RULE-007.

If any phase reveals a constraint conflict (e.g., the `selected_mechanism` cannot be threaded without crossing `argus/main.py:1081`'s do-not-modify region), halt and surface — A-class halt A12 fires on `argus/main.py:1081` modifications.

## Visual Review (N/A — backend-only)

S3b is backend-only. Zero UI changes (regression invariant 12).

## Definition of Done

- [ ] `Broker.refresh_positions(timeout_seconds=5.0)` ABC method added; backward-compatible default.
- [ ] `IBKRBroker.refresh_positions` Fix A single-flight serialization wrapper landed (`asyncio.Lock` + 250ms coalesce window per Round 3 C-R3-1).
- [ ] `SimulatedBroker.refresh_positions` no-op landed.
- [ ] 4 standalone-SELL emit sites wrapped with `_is_locate_suppressed` pre-check + `_is_locate_rejection` exception handler. DEF-158 3-branch side-check preserved verbatim.
- [ ] AC2.5 fallback with three branches + Branch 4 + HALT-ENTRY coupling under H1 active + Branch 4 throttle (1-hour cooldown).
- [ ] `_read_positions_post_refresh()` helper method on `OrderManager`.
- [ ] `ManagedPosition.halt_entry_until_operator_ack: bool = False` field added.
- [ ] RiskManager Check 0 extended to reject entries on positions with `halt_entry_until_operator_ack=True` (per-position granularity).
- [ ] `argus/api/routes/positions.py` halt-clear endpoint + `scripts/clear_position_halt.py` CLI tool.
- [ ] `time.monotonic()` substituted at all suppression-timeout sites; `time.time()` regression test passes.
- [ ] FAI #10 falsifying spike (`test_concurrent_callers_serialized_by_single_flight_lock`) green WITH mitigation; race observable WITHOUT mitigation.
- [ ] All 8 effective S3b path-2 tests + 4 HALT-ENTRY/RiskManager/throttle/monotonic tests + 1 concurrent-caller spike = 13 new tests, all passing.
- [ ] All existing pytest still passing (≥ 5,269 baseline).
- [ ] Pre-existing flake count unchanged (regression invariant 11 / B-class halt B1).
- [ ] CI green per RULE-050.
- [ ] Close-out report written to file (DEC-330).
- [ ] **FAI #10 materialized in `falsifiable-assumption-inventory.md`** per D15 of `doc-update-checklist.md` — see Close-Out section below for verbatim text.
- [ ] Tier 2 review completed via @reviewer subagent.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| `git diff HEAD~1 -- argus/execution/order_manager.py` shows no edits to DEF-158 3-branch side-check region (`BUY → resubmit / SELL → alert+halt / unknown → halt`) | Manual diff inspection + `tests/execution/order_manager/test_def204_session3_retry_side_check.py` green (regression invariant 8) |
| `git diff HEAD~1 -- argus/execution/order_manager.py` shows no edits to DEC-385's `phantom_short_retry_blocked` emitter source — only NEW call sites that reuse the emitter | Manual diff inspection (regression invariant 5) |
| `git diff HEAD~1 -- argus/execution/ibkr_broker.py` shows no edits to `place_bracket_order` OCA threading or `_handle_oca_already_filled` | Manual diff inspection (regression invariant 6) |
| `git diff HEAD~1 -- argus/main.py` shows ONLY the construction-call-site modification (passing `selected_mechanism=...` keyword) | Manual diff inspection; if any other change present, A-class halt A12 fires |
| `git diff HEAD~1 -- argus/models/trading.py` returns empty | Existing baseline; out-of-scope file |
| `git diff HEAD~1 -- argus/execution/alpaca_broker.py` returns empty | Existing baseline (DEF-178 future scope) |
| `git diff HEAD~1 -- frontend/` AND `argus/ui/` returns empty | Regression invariant 12 / B-class halt B8 |
| `grep -nE "time\.time\(\)" argus/execution/order_manager.py` returns zero hits in suppression-timeout-related code paths | H-R3-1 / regression invariant 31 |
| `grep -n "_REFRESH_POSITIONS_COALESCE_WINDOW_SECONDS" argus/execution/ibkr_broker.py` returns 1 hit | Round 3 C-R3-1 / regression invariant 28 |
| `grep -n "halt_entry_until_operator_ack" argus/execution/order_manager.py` returns ≥3 hits (field decl, set site, clear/read sites) | AC2.8 / regression invariant 24 |
| `grep -n "_branch4_last_alert_at" argus/execution/order_manager.py` returns ≥3 hits (init, set, clear) | M-R3-2 / regression invariant 34 |
| Test count ≥ 5,269 + 13 = 5,282 (S3b adds ~9 net per session-breakdown.md row; range 5,278–5,290 acceptable) | Close-out reports actual delta |
| Pre-existing flake count unchanged | DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/session-s3b-closeout.md
```

Do NOT just print the report in the terminal. Create the file, write the full report (including the structured JSON appendix) to it, and commit it.

### MANDATORY: Materialize FAI #10 per D15 of `doc-update-checklist.md`

After the close-out report is written and CI is green, materialize FAI #10 in `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md` per D15 of `docs/sprints/sprint-31.92-def-204-round-2/doc-update-checklist.md`:

1. Open `falsifiable-assumption-inventory.md`.
2. Append a new row to the main inventory table (entry #10) with the verbatim text from `round-3-disposition.md` § 6.1 (reproduced below). Update the inventory's preamble line `## Inventory (9 entries)` to `## Inventory (10 entries)`.
3. Mark the status field as `**falsified — green S3b spike (commit: <SHA>)**` if `test_concurrent_callers_serialized_by_single_flight_lock` passed; otherwise mark `**partially falsified — see S3b close-out**` and explain. Include a cross-reference: `Cross-layer falsification: scheduled in S5c CL-7 (status will flip to falsified at S5c close).`
4. Remove FAI #10's entry from the "Pending FAI extensions committed in `round-3-disposition.md`" subsection (since it has now been promoted into the main table). Leave FAI #11's pending entry intact (S4a-ii materializes #11).
5. Commit the doc change with message referencing D15 + the S3b close-out commit SHA.

**Verbatim text for FAI #10 main-table row (per `round-3-disposition.md` § 6.1):**

> | 10 | `Broker.refresh_positions()` synchronizes broker round-trip per-caller — concurrent callers each correctly correlate their `wait_for` return with their own `reqPositions()` invocation, OR the implementation explicitly serializes concurrent callers via single-flight pattern with coalesce window. The AC2.5 broker-verification-at-timeout fallback's correctness depends on this. | **Falsifying spike:** S3b sub-spike spawns N=20 coroutines calling `refresh_positions()` near-simultaneously (≤10ms separation) WITHOUT serialization mitigation; mocked-await injection between A's `reqPositions()` and B's `reqPositions()` with deterministic broker-state-change between; assert the race IS observable (stale-for-B classification). Then with the Fix A serialization mitigation enabled, assert the race is NOT observable. Cross-layer falsification at CL-7 in S5c. | **falsified — green S3b spike (commit: \<SHA from S3b close-out commit\>)**. Cross-layer falsification: scheduled in S5c CL-7 (status will flip to falsified at S5c close). |

If S3b's regression test failed for any reason, halt before materialization and surface to operator per Sprint Abort Condition #9 — Fix A spike failure routes to Phase A re-entry retroactively.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, AND FAI #10 is materialized, invoke the @reviewer subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.92-def-204-round-2/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.92-def-204-round-2/session-s3b-closeout.md`
3. The diff range: `git diff HEAD~2..HEAD` (covers both the implementation commit and the FAI materialization commit; confirm exact range during review).
4. The test command: `python -m pytest tests/execution/order_manager/ tests/execution/test_ibkr_broker.py tests/execution/test_ibkr_broker_concurrent_callers.py -n auto -q` (scoped per DEC-328; non-final session).
5. Files that should NOT have been modified:
   - `argus/main.py` beyond the OrderManager construction-call-site keyword addition
   - `argus/execution/order_manager.py` DEF-158 3-branch side-check region
   - `argus/execution/ibkr_broker.py::place_bracket_order` and `_handle_oca_already_filled`
   - `argus/models/trading.py`
   - `argus/execution/alpaca_broker.py`
   - `argus/data/alpaca_data_service.py`
   - `frontend/`, `argus/ui/`
   - `workflow/` submodule

The @reviewer will produce its review report at:

```
docs/sprints/sprint-31.92-def-204-round-2/session-s3b-review.md
```

The verdict JSON is fenced with ` ```json:structured-verdict `.

## Post-Review Fix Documentation

Same pattern as the implementation-prompt template — see template §"Post-Review Fix Documentation". If @reviewer reports CONCERNS and the findings are fixed within this session, append "Post-Review Fixes" to `session-s3b-closeout.md` and "Post-Review Resolution" to `session-s3b-review.md`. Update the verdict JSON to `CONCERNS_RESOLVED`. ESCALATE findings must NOT be fixed without human review.

## Session-Specific Review Focus (for @reviewer)

1. **Fix A single-flight serialization correctness.** Verify the `asyncio.Lock` + 250ms coalesce-window pattern at `IBKRBroker.refresh_positions`. Check that:
   - `_refresh_positions_lock` is `asyncio.Lock`, not `threading.Lock`.
   - The post-acquisition re-check inside the `async with` block prevents the lost-update race (coroutine B awaiting the lock while A synchronizes; B should coalesce on A's just-recorded timestamp).
   - `_last_refresh_synchronized_at` is updated AFTER `wait_for` succeeds, NOT before.
   - The 250ms constant lives at module scope as `_REFRESH_POSITIONS_COALESCE_WINDOW_SECONDS` (grep-discoverable).
   - The FAI #10 falsifying spike (`test_concurrent_callers_serialized_by_single_flight_lock`) genuinely exercises the race in mode (a) and confirms it's gone in mode (b). The pair-wise comparison is what falsifies FAI #10; a single-mode test is insufficient.

2. **AC2.5 three-branch + Branch 4 + HALT-ENTRY coupling correctness.** Verify:
   - Branch 1 (broker-zero) clears `_locate_suppressed_until[position.id]`; no alert.
   - Branch 2 (expected-long with shares ≥ remaining) clears the dict entry; no alert.
   - Branch 3 (unexpected) publishes `phantom_short_retry_blocked` via the existing DEC-385 emitter (NOT a new emitter); clears the dict entry.
   - Branch 4 (refresh-failure) publishes the SAME alert with `verification_stale: True` metadata; does NOT clear the dict entry; HALT-ENTRY fires ONLY when `_selected_mechanism == "h1_cancel_and_await"`.
   - Branch 4 throttle: 1-hour per-position cooldown; second firing within window logs `branch_4_throttled: true` at INFO; HALT-ENTRY persists across both firings.

3. **DEF-158 3-branch side-check verbatim preservation.** A-class halt A5 — the most critical regression check. Inspect the `_check_flatten_pending_timeouts` body line-by-line; verify that:
   - The BUY → resubmit branch is unchanged.
   - The SELL → alert+halt branch is unchanged.
   - The unknown → halt branch is unchanged.
   - The Path #2 NEW detection sits at the `place_order` exception (NOT inside the side-check switch).

4. **`time.monotonic()` substitution exhaustiveness.** Run a grep for `time.time()` against the diff; flag any remaining call sites in suppression-timeout-related code paths. The `OrderManagerConfig.locate_suppression_seconds` validator footnote should reference monotonic-time semantics.

5. **`halt_entry_until_operator_ack` field-ownership clarity.** S3b adds the field to `ManagedPosition`; S4a-i references it. Verify the field is added EXACTLY ONCE (S3b OR S4a-i, not both); the close-out should disclose which session owns the addition. If S4a-i has not landed, S3b owns it; if S4a-i lands first via reordering, S3b should reference the existing field.

6. **RiskManager Check 0 per-position granularity.** Test 9 must verify that an entry signal for a DIFFERENT `ManagedPosition.id` on the same symbol is NOT rejected (per AC2.8: per-position granularity, not per-symbol).

7. **Construction-surface modification scope.** `argus/main.py` must show ONLY the OrderManager keyword-argument addition. Any other `argus/main.py` change is A-class halt A12.

8. **`SimulatedBroker.refresh_positions` no-op-only.** Search for any code in `simulated_broker.py` that mutates state in `refresh_positions` — if found, this is the exact behavior SbC §"Out of Scope" #18 prohibits.

9. **FAI #10 materialization timing.** Verify the doc commit happened AFTER the implementation commit AND only when the regression test was green. Verify `falsifiable-assumption-inventory.md`'s preamble updated `9 entries` → `10 entries`. Verify the pending-FAI-#10 subsection had FAI #10 removed (FAI #11 still pending).

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`.

Of particular relevance to S3b (✓-mandatory at S3b per the Per-Session Verification Matrix):

- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** PASS — `phantom_short_retry_blocked` emitter unchanged; Branch 4 metadata extends but does NOT replace.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** PASS — `place_bracket_order` OCA threading unchanged; `_handle_oca_already_filled` unchanged.
- **Invariant 7 (DEC-388 alert observability):** PASS — POLICY_TABLE unchanged at S3b (the 14th `sell_ceiling_violation` entry is S4a-i).
- **Invariant 8 (DEF-158 3-branch side-check verbatim):** PASS — A-class halt A5 fires if violated. Inspect line-by-line.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** PASS — any new SELL-related logic must use OCA threading via `position.oca_group_id` OR carry `# OCA-EXEMPT:` comment.
- **Invariant 10, 11, 12:** PASS — test count ≥ 5,269 baseline; pre-existing flake count unchanged; frontend immutable.
- **Invariant 14 (Path #2 fingerprint + position-keyed dict + broker-verification):** ESTABLISHED — broker-verification at AC2.5 lands here.
- **Invariant 21 (broker-verification three-branch coverage):** ESTABLISHED — three S3b tests cover Branches 1/2/3.
- **Invariant 24 (HALT-ENTRY under H1 + refresh fail):** ESTABLISHED — test 11's mechanism-conditional behavior covers this.
- **Invariant 25 (Branch 4 + `SimulatedBrokerWithRefreshTimeout` fixture):** PARTIAL — Branch 4 emission landed at S3b; the dedicated fixture-based unit test lives at S5c per Decision 5 / Tier 3 item E.
- **Invariant 28 (NEW per Round 3 C-R3-1 — single-flight serialization):** ESTABLISHED — Fix A wrapper + `test_concurrent_callers_serialized_by_single_flight_lock`.
- **Invariant 30 (NEW per Round 3 M-R3-4 — `_read_positions_post_refresh` helper):** ESTABLISHED — helper introduced; AST-no-await scan extension lands at S4a-ii.
- **Invariant 31 (NEW per Round 3 H-R3-1 — `time.monotonic()`):** ESTABLISHED — substitution at all suppression-timeout sites + regression test 12.
- **Invariant 32 (NEW per Round 3 H-R3-3 — RiskManager Check 0 + halt-clear endpoint):** ESTABLISHED — tests 9 + 10 cover.
- **Invariant 34 (NEW per Round 3 M-R3-2 — Branch 4 throttle):** ESTABLISHED — test 11.

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`.

### A. Mandatory Halts (Tier 3 architectural review automatically fires)

Of particular relevance to S3b:

- **A4** (Any session's diff modifies a DEC-385/386/388 surface listed in the SbC "Do NOT modify" list beyond explicit additive points). Halt; revert; escalate Tier 3.
- **A5** (DEF-158 retry 3-branch side-check structure modified). Halt; SbC §"Edge Cases to Reject" #13 violation. The most critical S3b check.
- **A6** (Tier 2 review verdict CONCERNS or ESCALATE). Halt; iterate within session for CONCERNS; operator decides for ESCALATE.
- **A12** (any session's diff touches `argus/main.py::check_startup_position_invariant`, `_startup_flatten_disabled`, the `reconstruct_from_broker()` call site, OR `argus/execution/order_manager.py::reconstruct_from_broker` BODY beyond the single-line `is_reconstructed = True` addition — Sprint 31.94 D1+D2 surfaces). Halt; SbC §"Do NOT modify" #5 violation. The OrderManager construction-call-site keyword addition is the EXCEPTION; any other `argus/main.py` change in S3b fires A12.
- **A13** (spike artifacts older than 30 days at first post-merge paper session). Operational regression — applies post-merge.
- **A14** (Round 3 verdict produces ≥1 Critical finding). Decision 7 routing applies; Round 3 Operator Override Log Entry per `escalation-criteria.md` § Round 3 Operator Override Log Entry has already been invoked for C-R3-1 — Fix A spike failure routes to Sprint Abort Condition #9.
- **A17** (NEW per Tier 3 item A — synchronous-update invariant violation): not S3b's primary surface, but a callback-path leak that this session's coupling fails to anticipate would surface here.
- **A18** (NEW per Tier 3 item C — Branch 4 + H1 active without HALT-ENTRY firing). ESTABLISHES at S3b — if the regression test for HALT-ENTRY coupling fails, A18 fires.

### B. Mandatory Halts (Tier 3 not required; operator + Tier 2 reviewer disposition)

- **B1** (pre-existing flake count increases). Per RULE-041, file DEF entry on first observation.
- **B3** (pytest baseline ends below 5,269). Halt; investigate.
- **B4** (CI fails on session's final commit AND failure is NOT a documented pre-existing flake). Halt per RULE-050.
- **B5** (structural anchor referenced in impl prompt does not match repo state during pre-flight). Re-anchor against actual structural anchors. Disclose under RULE-038.
- **B6** (a do-not-modify-list file appears in `git diff`). Revert.
- **B7** (test runtime degrades >2× from baseline OR a single test exceeds 60s). The FAI #10 falsifying spike could plausibly add latency; benchmark and decide whether to mock the propagation.
- **B8** (frontend modification — zero scope). Revert.
- **B12** (AC2.5 broker-verification-at-timeout fails or returns stale data). Halt at S3b OR halt sprint if observed post-merge.

### C. Soft Halts (Continue with extra caution + close-out flag)

- **C1** (out-of-scope improvements). Document in close-out under "Deferred Items"; do NOT fix.
- **C5** (uncertain whether a change crosses do-not-modify boundary). Pause; consult SbC; escalate to operator before making the change.
- **C6** (line numbers drift 1–5 from spec). Continue; document actual line numbers in close-out for next session's reference.
- **C12** (`--allow-rollback` flag verification deferred to S4b — informational at S3b).

### Sprint Abort Conditions (especially relevant to S3b)

- **#9 (NEW per Round 3 C-R3-1 — Fix A serialization spike failure):** If `test_concurrent_callers_serialized_by_single_flight_lock` returns the race observable WITH the mitigation enabled (i.e., the lock + coalesce-window pattern fails to serialize), the override is empirically retracted and Phase A re-entry retroactively reactivates. Operator decision required to escalate; default disposition is sprint halt + Phase A re-entry. **This is the binding contract on the Round 3 operator override per `round-3-disposition.md` § 1.**

---

*End Sprint 31.92 Session S3b implementation prompt.*
