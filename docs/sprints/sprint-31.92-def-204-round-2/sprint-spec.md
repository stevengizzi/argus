# Sprint 31.92: DEF-204 Round 2 — Concurrent-Trigger Race + Locate-Rejection Retry Storm + Long-Only SELL-Volume Ceiling with Pending Reservation + DEF-212 Constant Drift Wiring

> **Phase C artifact 3/9 (revised post-Round-2-Disposition + Phase A
> Re-entry + Phase A Tier 3 + Phase B re-run).** Reproduces the verbatim
> 9-entry FAI from `falsifiable-assumption-inventory.md`. Materializes all
> 14 Round-2 dispositions, all 7 settled operator decisions, and all 5
> Tier-3-mandated revisions A–E. Sprint goal closes DEF-204's two
> empirically-falsifying mechanism paths from the 2026-04-28 paper-session
> debrief plus structural defense-in-depth at L3 (ceiling) and L4 (DEF-212
> rider).
>
> **Revision lineage:** Round 1 (3C+4H+3M dispositions, 2026-04-28) →
> Round-1-revised 2026-04-29 → Round 2 (1C+5H+5M+3L; 14 dispositions
> operator-confirmed; A14 fired) → Phase A re-entry FAI (8 entries) +
> findings → **Phase A Tier 3 review #1 verdict REVISE_PLAN 2026-04-29
> (entry #9 + H-R2-1 scope extension + FAI #5 N≥100 + FAI #8 option (a) +
> ≥4 cross-layer tests + C-R2-1↔H-R2-2 coupling + 6 DEFs + 2 RSKs)** →
> Phase B re-run 2026-04-29 (5 of 8 Substantive vs Structural triggers
> fired; 7 settled operator decisions adopted) → **this Phase C revision
> 2026-04-29.**

---

## Goal

Close DEF-204's two empirically-falsifying mechanism paths from the
2026-04-28 paper-session debrief — Path #1 (trail-stop / bracket-stop
concurrent-trigger over-flatten on BITU) and Path #2 (locate-rejection-as-held
retry storm on PCT) — via spike-driven mechanism selection (H2 amend-stop-price
default / H4 hybrid fallback / H1 cancel-and-await last-resort) plus structural
defense-in-depth: position-keyed locate suppression with broker-verified
timeout, long-only SELL-volume ceiling with concurrency-safe pending-share
reservation pattern (synchronous-update invariant extended to ALL bookkeeping
callback paths per Tier 3 entry #9), reconstructed-position refusal posture,
DEF-212 `_OCA_TYPE_BRACKET` constant drift fix with operator-visible rollback
warning + `--allow-rollback` CLI gate. Materialize as DEC-390 with
structural-closure framing (NOT aggregate percentage claims per
process-evolution lesson F.5), backed by ≥5 cross-layer composition tests
proving the failure of any one layer is caught by another.

---

## Scope

### Deliverables

1. **Path #1 mechanism (L1 — `_trail_flatten`, `_resubmit_stop_with_retry`
   emergency-flatten branch, conditionally `_escalation_update_stop`).**
   Implement the S1a-spike-selected mechanism per Hypothesis Prescription
   hierarchy (H2 PRIMARY DEFAULT — amend bracket stop's `auxPrice` /
   H4 hybrid fallback — try amend, fall back to cancel-and-await on
   amend rejection / H1 last-resort — cancel-and-await before SELL).
   AMD-2 invariant framing is mechanism-conditional (preserved on H2;
   mixed on H4; superseded by AMD-2-prime on H1).

2. **Path #2 detection + position-keyed locate-rejection suppression with
   broker-verified timeout (L2 — `_flatten_position`, `_trail_flatten`,
   `_check_flatten_pending_timeouts`, `_escalation_update_stop`
   exception handlers).** Add `_LOCATE_REJECTED_FINGERPRINT` substring
   constant + `_is_locate_rejection()` helper in `argus/execution/ibkr_broker.py`
   mirroring DEC-386's `_is_oca_already_filled_error` pattern; add
   `OrderManager._locate_suppressed_until: dict[ULID, float]` keyed by
   `ManagedPosition.id` (NOT symbol — cross-position safety per
   Round-1 H-2). Wire suppression detection at `place_order` exception
   in 4 standalone-SELL paths with pre-emit suppression check.
   Suppression-timeout fallback queries broker for actual position state
   BEFORE alert emission (Round-1 H-3 + Round-2 C-R2-1) via new
   `Broker.refresh_positions(timeout_seconds=5.0)` ABC method;
   three-branch classification (zero / expected-long / unexpected) + Branch 4
   (`verification_stale: true`) on refresh failure + HALT-ENTRY coupling
   under H1 active AND refresh failure (per Tier 3 item C).

3. **Long-only SELL-volume ceiling with concurrency-safe pending-share
   reservation + reconstructed-position refusal posture (L3 — guarded at
   all 5 standalone-SELL emit sites; bracket placement EXCLUDED per H-1).**
   Add THREE fields on `ManagedPosition`: `cumulative_pending_sell_shares: int = 0`
   (incremented synchronously at place-time before `await`; decremented on
   cancel/reject; transferred to filled on fill — closes Round-1 C-1 asyncio
   yield-gap race), `cumulative_sold_shares: int = 0` (incremented at confirmed
   SELL fill), and `is_reconstructed: bool = False` (set True in
   `reconstruct_from_broker`; refusal posture for ARGUS-emitted SELLs per
   Round-1 C-2). Atomic `_reserve_pending_or_fail()` synchronous method per
   H-R2-1, with AST-no-await regression guard + mocked-await injection test.
   **Synchronous-update invariant extended to all bookkeeping callback paths
   per Tier 3 items A + B: `on_fill`, `on_cancel`, `on_reject`,
   `_on_order_status`, and `_check_sell_ceiling` multi-attribute read.**
   `_check_sell_ceiling()` accepts `is_stop_replacement: bool=False` per
   H-R2-5 — exemption permitted ONLY at `_resubmit_stop_with_retry` normal-retry
   path (AST callsite-scan regression guard with 3 reflective-call
   sub-tests per Decision 3 / FAI #8 option (a)). New `sell_ceiling_violation`
   alert type, `POLICY_TABLE` 14th entry (`operator_ack_required=True`,
   `auto_resolution_predicate=None`); AST exhaustiveness regression guard
   updated. AC2.7 `_pending_sell_age_seconds` watchdog **auto-activates** from
   `auto` to `enabled` on first observed `case_a_in_production` event per
   Decision 4.

4. **DEF-212 `_OCA_TYPE_BRACKET` constant drift wiring + operator-visible
   rollback warning + `--allow-rollback` CLI gate (L4).** `OrderManager.__init__`
   accepts `bracket_oca_type: int` keyword argument; `argus/main.py`
   construction call site passes `config.ibkr.bracket_oca_type`; 4
   occurrences of `_OCA_TYPE_BRACKET = 1` module constant replaced by
   `self._bracket_oca_type`; module constant deleted; grep regression guard.
   **Dual-channel CRITICAL warning** per H-R2-4 (combined): ntfy.sh
   `system_warning` urgent AND canonical-logger CRITICAL with phrase
   "DEC-386 ROLLBACK ACTIVE" when `bracket_oca_type != 1` AND
   `--allow-rollback` flag present. **Exit code 2 + stderr FATAL banner**
   when `bracket_oca_type != 1` AND `--allow-rollback` flag absent (AC4.7
   per H-R2-4). `IBKRConfig.bracket_oca_type` Pydantic validator UNCHANGED
   — runtime-flippability preserved per DEC-386 design intent.

5. **Falsifiable end-to-end in-process validation (S5a + S5b + S5c).**
   Path #1 + Path #2 + composite + restart-during-active-position +
   cross-layer composition tests. Validates IN-PROCESS LOGIC against
   SimulatedBroker (and `SimulatedBrokerWithRefreshTimeout` fixture for
   Branch 4); does NOT validate IBKR API timing, network packet loss
   during cancel/amend propagation, IBKR's actual `modifyOrder` response
   timing, or concurrent fill arrival ordering across positions in
   production. Cessation criterion #5 (5 paper sessions clean post-seal)
   is the production-validation gate.

6. **DEC-390 materialization (sprint-close).** Four-layer structural-closure
   framing (NOT aggregate percentage claims per process-evolution lesson
   F.5). 6 DEFs filed by Tier 3 (DEF-FAI-CALLBACK-ATOMICITY,
   DEF-CROSS-LAYER-EXPANSION, DEF-FAI-N-INCREASE, DEF-FAI-2-SCOPE,
   DEF-FAI-8-OPTION-A, DEF-SIM-BROKER-TIMEOUT-FIXTURE). 7 RSKs filed
   (5 sprint-class + 2 Tier-3-class).

### Acceptance Criteria

#### Deliverable 1 (Path #1 mechanism — mechanism-conditional)

- **AC1.1:** `total_sold ≤ position.shares_total` invariant holds for all
  Path #1 trail-flatten dispatches across the canonical BITU 13:41 trace
  scenario (S2a: synthetic SimulatedBroker fixture + composite at S5a).
- **AC1.2 (mechanism-conditional, H2):** IF S1a selected H2 amend-stop-price
  — `IBKRBroker.modify_order(stop_order_id, new_aux_price)` is called
  BEFORE any `place_order(SELL)` invocation; mock-asserted in
  `test_path1_h2_amend_called_before_any_sell_emit`. AMD-2 invariant
  preserved.
- **AC1.2 (mechanism-conditional, H4):** IF S1a selected H4 hybrid —
  parametrized over (amend-success path, amend-failure-fallback path):
  amend-success path asserts NO standalone SELL emission;
  amend-failure-fallback path asserts `cancel_all_orders(symbol,
  await_propagation=True)` is called BEFORE `place_order(SELL)`. AMD-2
  invariant preserved on amend-success; AMD-2-prime asserted on
  cancel-fallback.
- **AC1.2 (mechanism-conditional, H1):** IF S1a selected H1 cancel-and-await
  (last-resort) — `cancel_all_orders(symbol, await_propagation=True)` is
  called BEFORE `place_order(SELL)`. AMD-2 invariant superseded by
  AMD-2-prime; unprotected window bounded by `cancel_propagation_timeout
  ≤ 2s` per DEC-386 S1c.
- **AC1.3 (extended surface):** AC1.2 mechanism applied to
  `_resubmit_stop_with_retry` emergency-flatten branch (DEC-372 retry-cap
  exhausted). Asserted at S2b. AC1.4 (existing AMD-8 + AMD-4 guards
  preserved). Conditionally extended to `_escalation_update_stop` IFF
  S1a confirmed amend semantics apply or cancel-and-await translates
  cleanly.
- **AC1.5 (mechanism-conditional AMD-2 framing):** AMD-2 invariant is
  PRESERVED under H2 (default), MIXED under H4 (preserved on amend-success;
  superseded on cancel-fallback), and SUPERSEDED by AMD-2-prime under H1
  (last-resort). DEC-390 entry must explicitly call out the framing for
  the chosen mechanism.
- **AC1.6 (operator-audit logging — conditional on H1 OR H4-with-fallback-active):**
  Structured log line emitted on every cancel-and-await dispatch
  (whether last-resort under H1 or fallback under H4) with required
  keys: `event="amd2_supersede"`, `symbol`, `position_id`,
  `mechanism ∈ {"h1_cancel_and_await", "h4_fallback"}`,
  `cancel_propagation_ms`. Asserted at S2a + S2b (conditional on S1a's
  `selected_mechanism` field).

#### Deliverable 2 (Path #2 detection + suppression + broker-verified timeout)

- **AC2.1:** `_is_locate_rejection(error: BaseException) -> bool` returns
  True for IBKR error matching the `_LOCATE_REJECTED_FINGERPRINT`
  substring (case-insensitive via `str(error).lower()`); returns False
  for all other 201 errors (margin, OCA-already-filled, price-protection).
  Substring captured by S1b spike. Helper accepts `BaseException` to
  mirror DEC-386's `_is_oca_already_filled_error` shape.
- **AC2.2:** `_is_locate_suppressed(position, now)` returns True iff
  `now < self._locate_suppressed_until.get(position.id, 0.0)` — keyed by
  `ManagedPosition.id` ULID per Round-1 H-2 (NOT symbol; cross-position
  safety preserved).
- **AC2.3:** Locate-rejection at any of the 4 standalone-SELL paths
  triggers suppression-dict entry: `_locate_suppressed_until[position.id]
  = time.time() + config.locate_suppression_seconds`.
- **AC2.4:** Subsequent SELL emit attempts at the same `ManagedPosition.id`
  during the suppression window are skipped (no broker call). Other
  `ManagedPosition`s on the same symbol are NOT affected (cross-position
  safety per Round-1 H-2).
- **AC2.5 (broker-verified suppression-timeout fallback — three branches +
  Branch 4 + HALT-ENTRY coupling per Tier 3 item C):**
  - Suppression-timeout fallback FIRST calls
    `await self._broker.refresh_positions(timeout_seconds=5.0)` (new ABC
    method per C-R2-1).
  - **Branch 4 (`verification_stale: true`):** if `refresh_positions`
    raises or times out, publish `phantom_short_retry_blocked` alert with
    metadata `{verification_stale: True, verification_failure_reason:
    type(exc).__name__, position_id, symbol}`. **C-R2-1↔H-R2-2 coupling
    per Tier 3 item C:** if H1 is the active mechanism AND Branch 4 fires,
    additionally mark position `halt_entry_until_operator_ack=True`. No
    further SELL attempts on the position; no phantom short. Operator-driven
    resolution.
  - On refresh success, query `broker.get_positions()` and apply
    three-branch classification:
    - **Branch 1 (broker shows zero):** held order resolved cleanly. Log
      INFO; clear `_locate_suppressed_until[position.id]` entry; no alert.
    - **Branch 2 (broker shows expected long with shares ≥
      `position.shares_remaining`):** no phantom short. Log INFO; clear
      dict entry; no alert.
    - **Branch 3 (broker shows short OR quantity divergence OR unknown
      side):** publish `phantom_short_retry_blocked` SystemAlertEvent
      via DEC-385's existing emitter (preserved verbatim).
  - Suppression-window expiration emits at most ONE alert per
    `ManagedPosition.id` per session.
- **AC2.6 (`on_position_closed` event coverage — M-R2-2):** Suppression-dict-clear
  logic exercised by all 4 ARGUS position-close paths (broker confirms zero
  shares; `_flatten_pending` clears; `ManagedPosition` removed from
  active-positions dict; the canonical `on_position_closed` close-path).
  Regression test at S3b asserts dict entry cleared on each path.
- **AC2.7 (`_pending_sell_age_seconds` watchdog — M-R2-1 + Decision 4
  auto-activation):** Watchdog monitors per-position pending-SELL age;
  fires when `now - position.last_sell_emit_time > pending_sell_age_seconds`
  AND no fill observed. Activated via config field
  `order_management.pending_sell_age_watchdog_enabled` with values
  `auto` (default) / `enabled` / `disabled`. **`auto` mode flips to
  `enabled` on first observed `case_a_in_production` event** in production
  paper trading. NOT manual operator activation per Decision 4. Provides
  the structural fallback for any unmodeled locate-rejection string variant
  (FAI #4 mitigation).

#### Deliverable 3 (Long-only SELL-volume ceiling — synchronous-update invariant extended per Tier 3 items A + B)

- **AC3.1 (5 state transitions + synchronous-update invariant on ALL
  bookkeeping callback paths per Tier 3 items A + B):** Pending-reservation
  state machine enumerates 5 transitions:
  1. **Place-time increment** (synchronous, before `await place_order(...)`):
     `position.cumulative_pending_sell_shares += requested_qty` inside
     `_reserve_pending_or_fail` — H-R2-1 atomic method.
  2. **Cancel-time decrement:** `on_cancel` handler decrements
     `cumulative_pending_sell_shares` by cancelled qty.
  3. **Reject-time decrement:** `on_reject` handler decrements
     `cumulative_pending_sell_shares` by rejected qty.
  4. **Partial-fill transfer:** `on_fill` partial-fill processing
     decrements `cumulative_pending_sell_shares` by `filled_qty` AND
     increments `cumulative_sold_shares` by `filled_qty` — synchronously,
     no `await` between read and write.
  5. **Full-fill transfer:** `on_fill` full-fill processing decrements
     `cumulative_pending_sell_shares` by remaining AND increments
     `cumulative_sold_shares` by remaining — synchronously.
  **Synchronous-update invariant extends to all 5 paths AND to
  `_check_sell_ceiling` multi-attribute read (per Tier 3 items A + B /
  FAI entry #9).** AST-no-await scan + mocked-await injection regression
  applied to `_reserve_pending_or_fail`, `on_fill`, `on_cancel`,
  `on_reject`, `_on_order_status`, AND the multi-attribute read sequence
  in `_check_sell_ceiling` (asserted at S4a-ii). Preferred outcome of
  S4a-ii is zero production-code change with the test file establishing
  the regression guard.
- **AC3.2 (5 standalone-SELL emit sites guarded; bracket placement
  EXCLUDED per H-1):** Guards at `_trail_flatten`, `_escalation_update_stop`,
  `_resubmit_stop_with_retry`, `_flatten_position`,
  `_check_flatten_pending_timeouts`. Bracket placement
  (`place_bracket_order`) EXPLICITLY EXCLUDED — bracket children are placed
  atomically against a long position; total bracket-child quantity equals
  `shares_total` by construction; OCA enforces atomic cancellation per
  DEC-117 + DEC-386 S1a. T1/T2/bracket-stop FILLS still increment
  `cumulative_sold_shares` per AC3.1 (because they ARE real sells). Each
  guard goes through `_reserve_pending_or_fail(position, requested_qty)`
  per H-R2-1.
- **AC3.3 (alert emission on violation):** When `_check_sell_ceiling`
  refuses, emit `SystemAlertEvent(alert_type="sell_ceiling_violation",
  severity="critical", metadata={position_id, symbol, requested_qty,
  pending, sold, shares_total, emit_site})`; log CRITICAL; do NOT
  increment pending counter. Guards do NOT proceed to `place_order`.
- **AC3.4 (per-`ManagedPosition`, NOT per-symbol):** Multiple
  `ManagedPosition`s on the same symbol each have their own ceiling.
  Cross-position aggregation is the existing Risk Manager
  max-single-stock-exposure check at the entry layer (DEC-027), out of
  scope to modify here.
- **AC3.5 (canonical C-1 race test + AST guards per Tier 3 items A + B):**
  Two coroutines on same `ManagedPosition` both attempt SELL emission;
  first passes ceiling and increments pending; second sees pending and
  FAILS ceiling check; refuses SELL. Plus AST-no-await scan + mocked-await
  injection regression on `_reserve_pending_or_fail` (S4a-i) AND on all 5
  bookkeeping callback paths (S4a-ii per FAI entry #9).
- **AC3.6 (broker-confirmed initialization with DEC-369 immunity):**
  `reconstruct_from_broker`-derived positions initialize
  `cumulative_pending_sell_shares = 0`, `cumulative_sold_shares = 0`,
  `is_reconstructed = True`, `shares_total = abs(broker_position.shares)`.
  Composes additively with DEC-369 immunity — BOTH protections apply.
- **AC3.7 (`is_reconstructed` refusal posture):** `_check_sell_ceiling`
  returns False unconditionally on `position.is_reconstructed == True`,
  regardless of pending+sold+requested arithmetic. Refusal applies to
  ARGUS-emitted SELLs ONLY; operator-manual flatten via
  `scripts/ibkr_close_all_positions.py` is the only closing mechanism
  until Sprint 31.94 D3.
- **AC3.8 (config-gating, fail-closed):**
  `OrderManagerConfig.long_only_sell_ceiling_enabled = true` (default).
  When `false`, `_check_sell_ceiling` returns True unconditionally.
  Booleans only — no third state.
- **AC3.9 (`POLICY_TABLE` 14th entry):**
  `sell_ceiling_violation` policy entry: `operator_ack_required=True`,
  `auto_resolution_predicate=None` (manual-ack only). AST exhaustiveness
  regression guard updated to expect 14 entries.

#### Deliverable 4 (DEF-212 rider — dual-channel + `--allow-rollback`)

- **AC4.1:** `OrderManager.__init__(self, ..., bracket_oca_type: int)`
  accepts the new keyword argument; sets `self._bracket_oca_type = bracket_oca_type`.
- **AC4.2:** `argus/main.py` construction call site passes
  `bracket_oca_type=config.ibkr.bracket_oca_type`.
- **AC4.3:** Module constant `_OCA_TYPE_BRACKET = 1` deleted from
  `argus/execution/order_manager.py`. 4 use sites at OCA-thread sites
  (verified via grep at session start; absolute line numbers DIRECTIONAL
  ONLY per protocol v1.2.0+) replaced by `self._bracket_oca_type`. Grep
  regression guard `test_no_oca_type_bracket_constant_remains_in_module`.
- **AC4.4 (lock-step, NOT operational validity):** Flipping
  `bracket_oca_type` from 1 to 0 produces consistent `ocaType=0` on
  bracket children AND on standalone-SELL OCA threading (no divergence).
  Test docstring explicitly: "ocaType=0 disables OCA enforcement and
  reopens DEF-204; this test asserts the rollback path is consistent,
  not that the rollback is operationally safe."
- **AC4.5 (DEC-117 atomic-bracket invariants preserved byte-for-byte):**
  Existing regression test `test_dec386_oca_invariants_preserved_byte_for_byte`
  green throughout S4b.
- **AC4.6 (dual-channel CRITICAL warning — H-R2-4 combined):** When
  `bracket_oca_type != 1` AND `--allow-rollback` CLI flag is present,
  ARGUS emits:
  - **ntfy.sh `system_warning` urgent** with topic
    `argus_system_warnings`.
  - **Canonical-logger CRITICAL** with phrase "DEC-386 ROLLBACK
    ACTIVE: bracket_oca_type=N. OCA enforcement on bracket children is
    DISABLED. DEF-204 race surface is REOPENED. Operator must restore to
    1 and restart unless emergency rollback in progress."
  Both emissions captured at startup; tested via log-capture fixture in
  S4b (`test_startup_critical_warning_emitted_when_bracket_oca_type_zero`).
- **AC4.7 (`--allow-rollback` CLI flag gate per H-R2-4):**
  - `argus/main.py` parses `--allow-rollback` flag.
  - When `bracket_oca_type != 1` AND `--allow-rollback` flag absent:
    ARGUS exits with code 2 + stderr FATAL banner ("DEC-386 ROLLBACK
    REQUESTED WITHOUT --allow-rollback FLAG. Refusing to start.").
  - When `bracket_oca_type != 1` AND `--allow-rollback` flag present:
    AC4.6 dual-channel emission fires; ARGUS proceeds to start.
  - When `bracket_oca_type == 1`: `--allow-rollback` flag is ignored
    (no-op).

#### Deliverable 5 (Falsifiable in-process validation — S5a + S5b + S5c)

- **AC5.1 (in-process logic validation, NOT production safety evidence):**
  `scripts/validate_def204_round2_path1.py` produces
  `scripts/spike-results/sprint-31.92-validation-path1.json` with
  `path1_safe: true` AND `phantom_shorts_observed: 0` AND
  `total_sold_le_total_bought: true`. Validates IN-PROCESS LOGIC of Path #1
  mechanism via SimulatedBroker fixture. Does NOT validate IBKR API
  timing, network packet loss during cancel/amend propagation, IBKR's
  actual `modifyOrder` response timing, or concurrent fill arrival
  ordering across positions in production. Run at S5a; output committed
  as falsifiable in-process evidence per regression invariant 18 (analog
  of DEC-386's `PATH_1_SAFE` artifact, valid ≤30 days for the in-process
  invariant).
- **AC5.2 (in-process logic validation, NOT production safety evidence):**
  `scripts/validate_def204_round2_path2.py` produces
  `scripts/spike-results/sprint-31.92-validation-path2.json` with
  `path2_suppression_works: true` AND `sell_emits_per_position_within_window
  ≤ 1` AND `held_order_fill_propagates: true` AND
  `broker_verification_at_timeout_works: true`. Same scope qualifier as
  AC5.1. Run at S5b.
- **AC5.3 (Pytest test with JSON side-effect):** Composite validation
  implemented as Pytest integration tests in
  `tests/integration/test_def204_round2_validation.py` (test names
  `test_composite_validation_zero_phantom_shorts_under_load`,
  `test_composite_validation_ceiling_blocks_under_adversarial_load`,
  `test_composite_validation_multi_position_same_symbol_cross_safety`).
  Test fixture writes `scripts/spike-results/sprint-31.92-validation-composite.json`
  BEFORE assertion. Daily CI workflow runs the test and the artifact
  mtime tracks freshness. Assertions: under benign synthetic-broker load,
  `phantom_shorts_observed == 0` AND `ceiling_violations_observed == 0`;
  under adversarial synthetic-broker load (forced over-flatten attempts at
  all 5 standalone-SELL emit sites), `ceiling_violations_correctly_blocked
  ≥ 1`; multi-position cross-safety preserved.
- **AC5.4 (restart-during-active-position validation):**
  `tests/integration/test_def204_round2_validation.py::test_restart_during_active_position_refuses_argus_sells`
  — fixture: spawn ManagedPosition normally, partial-fill via T1, simulate
  restart by calling `reconstruct_from_broker()` (or directly setting
  `is_reconstructed=True` if test architecture requires), assert subsequent
  `_trail_flatten`, `_flatten_position`, `_check_flatten_pending_timeouts`,
  `_escalation_update_stop` invocations all refuse to emit SELL. Asserted
  at S5b.
- **AC5.5 (artifacts committed):** All three validation artifacts
  (`sprint-31.92-validation-{path1,path2,composite}.json`) committed to
  `main` BEFORE sprint-close (D14 doc-sync). Sprint cannot be sealed
  without these.
- **AC5.6 (Cross-Layer Composition Tests committed at S5c per Decision 5):**
  All 5 cross-layer composition tests (CL-1 through CL-5; see § "Defense-in-Depth
  Cross-Layer Composition Tests" below) committed in
  `tests/integration/test_def204_round2_validation.py`.
  `tests/integration/conftest_refresh_timeout.py` provides the
  `SimulatedBrokerWithRefreshTimeout` fixture variant (DEF-SIM-BROKER-TIMEOUT-FIXTURE)
  enabling in-process Branch 4 testing for CL-3 + a dedicated Branch 4
  unit test.

#### Deliverable 6 (DEC-390 materialization — structural-closure framing per process-evolution lesson F.5)

- **AC6.1:** DEC-390 written below in `docs/decision-log.md` at sprint-close.
  Four-layer structure: L1 Path #1 mechanism / L2 Path #2 fingerprint +
  position-keyed suppression + broker-verified timeout / L3 SELL-volume
  ceiling with pending reservation + reconstructed-position refusal + AC2.7
  watchdog auto-activation / L4 DEF-212 wiring + AC4.6 dual-channel + AC4.7
  `--allow-rollback` gate. Cross-References to DEC-385, DEC-386, DEC-388,
  DEF-204, DEF-212, Apr 28 paper-session debrief, S1a + S1b spike artifacts,
  S5a + S5b + S5c validation artifacts.
- **AC6.2:** `docs/dec-index.md` updated.
- **AC6.3 (structural-closure framing — NOT aggregate percentage claims per
  process-evolution lesson F.5):** Sprint 31.91's empirically-falsified
  `~98%` claim is acknowledged in DEC-390 Context section; DEC-386
  preserved unchanged (per Phase A leave-as-historical decision). DEC-390
  uses STRUCTURAL closure framing ("L1 closes Path #1 mechanism / L2
  closes Path #2 detection + position-keyed suppression + broker-verified
  timeout / L3 closes long-only ceiling with extended synchronous-update
  invariant + reconstructed-position refusal / L4 closes constant-drift
  hygiene with operator-visible rollback gate") rather than aggregate
  percentage claims. Reviewer halts on tokens like "comprehensive,"
  "complete," "fully closed," "covers ~N%."

### Defense-in-Depth Cross-Layer Composition Tests (mandatory per `templates/sprint-spec.md` v1.2.0; 5 tests committed per Decision 5)

DEC-390 claims defense-in-depth across 4 layers. Per
`templates/sprint-spec.md` v1.2.0, Sprint 31.92's regression checklist MUST
include cross-layer composition tests — scenarios where the failure of one
layer is supposed to be caught by another, asserting that the catch happens.
**Sprint 31.92 commits to 5 cross-layer composition tests** (above the
template's "at least one" floor; above Tier 3 sub-area D's 3-test floor)
delivered at S5c (NEW SESSION per Decision 5):

- **CL-1 (L1 fails → L3 catches):** Force `_reserve_pending_or_fail` false
  positive (mock the synchronous method to return True even when the
  ceiling would be exceeded). Verify the ceiling-violation invariant
  catches at reconciliation; locate-suppression-with-broker-verification
  alert path fires.
- **CL-2 (L4 fails → L2 catches):** Force startup with `bracket_oca_type
  != 1` AND `--allow-rollback` (the operator-confirmed rollback path).
  Verify under DEC-386 rollback that the emergency-flatten branch (Layer
  2 via `is_stop_replacement=False`) still ceiling-checks; this proves
  Layer 2 doesn't depend on Layer 4's enforcement.
- **CL-3 (L3 + L5 cross-falsification — FAI #2 + #5 + Tier 3 item C):**
  Force `Broker.refresh_positions()` timeout (Layer 3 fails) AND H1
  selection by S1a output. Verify the H-R2-2 HALT-ENTRY posture catches
  the composite — position marked `halt_entry_until_operator_ack=True`;
  no further SELL attempts; no phantom short. **Uses the new
  `SimulatedBrokerWithRefreshTimeout` fixture per Tier 3 item E /
  Decision 5 / DEF-SIM-BROKER-TIMEOUT-FIXTURE.**
- **CL-4 (L1 + L2; NEW per Tier 3 sub-area D):** Reservation succeeds but
  `is_stop_replacement` decision is wrong (e.g., emergency-flatten
  misclassified as stop-replacement); verify L3 ceiling catches the
  resulting over-flatten.
- **CL-5 (L2 + L3; NEW per Tier 3 sub-area D):** `is_stop_replacement`
  correctly disambiguates a stop-replacement (L2 grants exemption) AND
  locate-suppression for the position is active. Verify the protective
  stop-replacement path is allowed AND that Branch 4 does not falsely
  fire on it.

**CL-6 (rollback + locate-suppression interaction) is OUT of scope per
Decision 5** — deferred with rationale documented in
`docs/process-evolution.md`. L4's compositions with runtime layers (other
than CL-2) are weakly meaningful in the operationally-relevant case; the
trade-off between exhaustive coverage and bounded session count was
resolved in favor of bounded scope at this sprint.

Cross-layer tests are typically slow, ugly, and span multiple modules.
That is the cost of catching composition failures structurally rather
than after merge — the Origin comment in
`templates/sprint-spec.md` v1.2.0 explicitly references DEC-386's
empirical falsification on 2026-04-28 (60 phantom shorts via cross-layer
path that no single-layer test exercised) as the proximal trigger for
the requirement.

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Path #1 H2 amend latency | ≤ 50ms p95 (validated by S1a spike) | S1a spike measures `modifyOrder` round-trip on paper IBKR ≥50 trials; adversarial sub-axes per Decision 1 use worst-axis Wilson UB |
| Path #1 H1 cancel-and-await latency overhead per trail-flatten (fallback only) | ≤ 200ms p95 | S1a spike measures on paper IBKR; S5a fixture asserts under simulated propagation |
| Path #1 cancel-then-immediate-SELL stress (FAI #5) | 0 conflicts in N=100 trials (HARD GATE per Decision 2) | S1a strengthened sub-spike; if any conflict in 100 trials, H1 NOT eligible regardless of Wilson UB |
| `_check_sell_ceiling` per-call overhead | ≤ 10µs | S4a-i benchmark — `pytest --benchmark` on hot path |
| `_is_locate_rejection` per-call overhead | ≤ 5µs | S3a benchmark — string-lowercase + substring; trivial |
| `_locate_suppressed_until` dict lookup overhead | ≤ 5µs | S3b benchmark — single dict.get + float comparison |
| Broker-side verification at suppression-timeout (AC2.5) | ≤ 5.2s p95 worst-case (refresh round-trip + verification call; slow path by definition; once per position per session worst case) | S3b benchmark — single `refresh_positions()` + `get_positions()` call sequence |
| Pending reservation increment/decrement overhead | ≤ 1µs | S4a-i benchmark — synchronous integer arithmetic on `ManagedPosition` |
| Full-suite test runtime regression | ≤ +50s vs baseline 5,269 pytest (recalibrated per Tier 3 cumulative diff bound) | DEC-328 final-review full-suite measurement |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default | Validator |
|-----------|---------------|------------|---------|-----------|
| `order_manager.locate_suppression_seconds` | `OrderManagerConfig` | `locate_suppression_seconds` | **TBD-from-S1b spike (target p99+20%, likely 18000s = 5hr)** | `Field(default=<spike_value>, ge=300, le=86400)` |
| `order_manager.long_only_sell_ceiling_enabled` | `OrderManagerConfig` | `long_only_sell_ceiling_enabled` | `True` (fail-closed) | `Field(default=True)` |
| `order_manager.long_only_sell_ceiling_alert_on_violation` | `OrderManagerConfig` | `long_only_sell_ceiling_alert_on_violation` | `True` | `Field(default=True)` |
| `order_management.pending_sell_age_watchdog_enabled` | `OrderManagerConfig` | `pending_sell_age_watchdog_enabled` | `"auto"` | `Field(default="auto")` with `Literal["auto", "enabled", "disabled"]` validator. **NEW per Decision 4** — `auto` mode flips to `enabled` on first observed `case_a_in_production` event. |
| `(existing) ibkr.bracket_oca_type` | `IBKRConfig` | `bracket_oca_type` | `1` | `Field(default=1, ge=0, le=1)` — **EXISTING (no schema change); S4b consumes**. Runtime-flippability preserved per DEC-386 design intent. |

**CLI flag (NEW per H-R2-4):** `--allow-rollback` on `argus/main.py`.
Required to start ARGUS with `bracket_oca_type != 1`; absent ⇒ exit code
2 + stderr FATAL banner. Present ⇒ ntfy.sh `system_warning` urgent +
canonical-logger CRITICAL with phrase "DEC-386 ROLLBACK ACTIVE."

**Critical:** S1b spike output JSON must include
`recommended_locate_suppression_seconds: int` field. S3a impl prompt reads
this and bakes the value into the Pydantic field default at code-generation
time. If S1b returns INCONCLUSIVE (no released-held-orders observed in
spike trials per H6 rules-out condition), default falls back to 18000s
(5hr) with documented rationale: "Spike never observed a release event;
suppression-timeout fallback is the dominant code path; 5hr conservative
default with broker-verification-at-timeout (AC2.5) catches any actual
hold release."

**Regression checklist item:** "New `OrderManagerConfig` fields verified
against Pydantic model — YAML field names match Pydantic field names
exactly; CI test loads `config/system_live.yaml` and asserts no
unrecognized keys under `order_manager.*` (test added at S3a)."

## Dependencies

- Sprint 31.91 SEALED at HEAD (verified D14 sprint-close 2026-04-28).
  DEC-385 + DEC-386 + DEC-388 materialized.
- Sprint 31.915 SEALED at HEAD (verified — DEC-389 evaluation.db retention
  + VACUUM-on-startup).
- Phase 0 cross-reference renumbering edits applied to `CLAUDE.md` +
  `docs/roadmap.md` (verified 2026-04-29 via repo pull).
- Phase A re-entry FAI authored (`falsifiable-assumption-inventory.md`,
  9 entries post-Phase-C revision).
- Phase A Tier 3 review #1 verdict received and dispositioned
  (`tier-3-review-1-verdict.md`, REVISE_PLAN, 2026-04-29).
- Phase B re-run (`design-summary.md`, 2026-04-29).
- 7 settled operator decisions adopted verbatim (Decisions 1–7).
- Operator runs `scripts/ibkr_close_all_positions.py` daily until cessation
  criterion #5 satisfied (5 paper sessions clean post-Sprint-31.92 seal).
  Operator confirmed Apr 28 boot-time 43-short residue was missed-run human
  error, NOT a script defect.
- Spike outputs (S1a + S1b JSON artifacts) gate Phase D implementation
  prompts for S2a/S2b and S3a/S3b respectively. The implementation prompts
  are NOT generated until spike artifacts land and operator approves the
  chosen mechanism + suppression-window default.
- Paper IBKR Gateway accessible (account U24619949) for S1a + S1b spike
  measurements. Spike sessions are non-safe-during-trading; run during
  pre-market or after-hours. S1b additionally requires operator-curated
  list of ≥5 known hard-to-borrow microcap symbols (PCT-class) before
  session.
- Adversarial Round 3 verdict (full scope per `protocols/adversarial-review.md`
  v1.1.0 § Outcome C; supersedes Round-2 disposition's narrowest-scope
  recommendation) received and dispositioned per Decision 7 binding
  pre-commitment before Phase D prompt generation begins.

## Relevant Decisions

- **DEC-386 (Sprint 31.91 Tier 3 #1, 2026-04-27)** — 4-layer OCA-Group
  Threading + Broker-Only Safety. Closes DEF-204 OCA-cancellation race at
  IBKR layer. **Empirically falsified 2026-04-28** (60 NEW phantom shorts,
  debrief at `docs/debriefs/2026-04-28-paper-session-debrief.md`). DEC-386
  preserved unchanged; DEC-390 closes the residual paths structurally with
  concurrency-safe defense-in-depth. Constrains Sprint 31.92: S0/S1a/S1b/S1c
  surfaces preserved byte-for-byte; existing `# OCA-EXEMPT:` exemption
  mechanism re-used; existing `_is_oca_already_filled_error` re-used (NOT
  relocated this sprint); rollback escape hatch (`bracket_oca_type=0`)
  preserved with NEW startup-warning per AC4.6 + `--allow-rollback` CLI
  gate per AC4.7.
- **DEC-385 (Sprint 31.91, 2026-04-02 → 2026-04-28)** — 6-layer Side-Aware
  Reconciliation Contract. The `phantom_short_retry_blocked` alert path
  (used by DEF-158 retry side-check) is re-used by Path #2's broker-verified
  suppression-timeout fallback (Branches 3 + 4). Constrains Sprint 31.92:
  DEF-158's 3-branch side-check (BUY/SELL/unknown) preserved verbatim;
  Path #2 adds NEW upstream detection at `place_order` exception, not a
  4th branch.
- **DEC-388 (Sprint 31.91, 2026-04-28)** — Alert Observability Architecture.
  New `sell_ceiling_violation` alert type added to `POLICY_TABLE` per
  AC3.9. Existing `phantom_short_retry_blocked` re-used per AC2.5.
  Constrains Sprint 31.92: must update `POLICY_TABLE` and AST exhaustiveness
  regression guard.
- **DEC-372 (Sprint 27.95)** — Stop Resubmission Cap with Exponential
  Backoff. The emergency-flatten branch in `_resubmit_stop_with_retry`
  (where retry cap is exhausted) is one of Path #1's surfaces. DEC-372's
  cap mechanism preserved; AC1.3 adds the H2/H4/H1 mechanism to the
  emergency SELL.
- **DEC-369 (Sprint 27.95)** — Broker-Confirmed Reconciliation. AC3.6
  must compose with broker-confirmed positions: `cumulative_pending_sell_shares
  = 0`, `cumulative_sold_shares = 0`, `is_reconstructed = True`
  initialization; refusal posture for ARGUS-emitted SELLs preserves
  DEC-369 immunity (broker-confirmed positions remain operator-managed).
- **DEC-364 (Sprint 27.95)** — `cancel_all_orders()` no-args ABC contract.
  Path #1 H1/H4 fallback uses DEC-386 S0's `cancel_all_orders(symbol,
  await_propagation=True)` extended signature. DEC-364's no-args contract
  preserved.
- **DEC-345 (Sprint 27.7)** — Separate-DB pattern. `sell_ceiling_violation`
  alerts persist via existing `data/operations.db` infrastructure (DEC-388
  L3); no new DB.
- **DEC-328 (Sprint 23.5)** — Test suite tiering. Applied: S1a pre-flight =
  full suite; S1b–S5c pre-flights = scoped; all close-outs = full suite;
  non-final reviews = scoped; final review = full suite.
- **DEC-122 (Sprint 8)** — Per-signal time stops. The PCT canonical Path #2
  trace fired its first SELL via the time-stop path; AC2.3 + AC2.4 protect
  that path with position-keyed suppression.
- **DEC-117 (Sprint 7)** — Atomic bracket order placement. AC4.5 preserves
  this byte-for-byte. AC3.2 EXCLUDES bracket placement from ceiling check
  specifically to preserve DEC-117.

## Relevant Risks

### Severity Calibration Rubric application notes

Per `templates/sprint-spec.md` v1.2.0 § Severity Calibration Rubric:

- **MEDIUM-HIGH floor:** mitigation depends on operator action that has
  empirically failed within last 10 sprints, OR similar failure mode
  empirically observed within last 5 sprints.
- **HIGH floor:** mitigation depends on sprint-bounded fix and bound
  exceeds 4 weeks calendar OR 3 sprints, whichever longer.
- **CRITICAL floor:** failure mode produces unrecoverable financial loss
  or data loss within single trading session OR single execution window.

The disposition author may rate higher than the floor but not lower
without explicit reviewer sign-off.

### Risk register

- **RSK-DEC-386-DOCSTRING (Sprint 31.91)** — Time-bounded contract on
  `reconstruct_from_broker()` STARTUP-ONLY docstring; bound by Sprint
  31.94. Sprint 31.92 does NOT modify this surface (Sprint 31.94's
  responsibility per Phase 0 renumbering).

- **NEW RSK-DEC-390-AMEND (PRIMARY — proposed, conditional on H2 selection
  by S1a):** DEC-390 L1 selected H2 per S1a spike. The amend-stop-price
  path depends on IBKR's `modifyOrder` semantics being deterministic at
  sub-50ms latency. If a future IBKR API change introduces non-determinism,
  the mechanism degrades silently. Severity: **MEDIUM** (operational
  hygiene). Mitigation: AC1.2 mock regression test; quarterly operational
  re-validation; cessation criterion #5; spike artifact 30-day freshness
  check via A-class halt A13.

- **NEW RSK-DEC-390-CANCEL-AWAIT-LATENCY (FALLBACK — proposed, conditional
  on H1 or H4 selection by S1a):** AMD-2 invariant superseded by
  AMD-2-prime on cancel-and-await branch. Unprotected window bounded by
  `cancel_propagation_timeout ≤ 2s` per DEC-386 S1c. Severity: **MEDIUM**
  (operational hygiene; conditional on mechanism). Mitigation: AC1.6
  operator-audit logging; documented trade-off; cessation criterion #5.

- **NEW RSK-DEC-390-FINGERPRINT (proposed, unconditional):**
  `_is_locate_rejection()` substring fingerprint depends on IBKR's exact
  rejection error string. Severity: **MEDIUM** (operational hygiene).
  Mitigation: S5b validation against synthetic locate-rejection fixture;
  quarterly operational re-validation; CI freshness check (90 days).

- **NEW RSK-CEILING-FALSE-POSITIVE (proposed, unconditional):** DEC-390
  L3 ceiling uses two-counter reservation pattern. Edge cases: (a) broker
  fill callback arrives out-of-order; (b) partial-fill granularity differs
  between SimulatedBroker and IBKR; (c) `cumulative_pending_sell_shares`
  not decremented correctly on cancel/reject; (d) C-1 race scenario fires
  unexpectedly (two coroutines both pass ceiling). Severity: **MEDIUM**
  (mitigated by S5b composite test + A-class halt A11). **Synchronous-update
  invariant per Tier 3 items A + B + FAI entry #9 extends mitigation to
  all bookkeeping callback paths via S4a-ii AST-no-await scan + mocked-await
  injection regression.**

- **NEW RSK-RECONSTRUCTED-POSITION-DEGRADATION (proposed, unconditional,
  time-bounded by Sprint 31.94 D3):** AC3.7's `is_reconstructed = True`
  refusal posture blocks ARGUS-emitted SELLs on reconstructed positions
  until Sprint 31.94 D3's policy decision lands. Severity: **MEDIUM-HIGH**
  per Severity Calibration Rubric — the mitigation depends on operator
  daily-flatten action that empirically failed Apr 28 (27 of 87
  ORPHAN-SHORT detections from a missed run; per H-R2-3). Sprint Abort
  Condition #7 trigger lowered from 4 weeks to 2 weeks per H-R2-3.
  Mitigation: `_startup_flatten_disabled` (IMPROMPTU-04) blocks
  reconstruction entirely on most non-clean broker states; operator
  daily-flatten (acknowledged-fallible safety net); A-class halts A15 +
  A16; Sprint 31.94 D3 retires the conservative posture.

- **NEW RSK-SUPPRESSION-LEAK (proposed, unconditional, partially-mitigated
  by AC2.5 broker-verification + Branch 4):** `OrderManager._locate_suppressed_until`
  dict accumulates entries; cleared on (a) fill callback, (b) position close,
  (c) suppression-window timeout fallback (AC2.5 with broker-verification
  + Branch 4). Mid-session reconnect would leave stale entries until
  timeout fires. Severity: **LOW** (operational; structural mitigation in
  place). AC2.5 broker-verification eliminates false-positive alert class
  even when stale dict entries persist post-reconnect; Branch 4 fires
  alert with `verification_stale: true` metadata when refresh fails;
  Tier 3 item C couples HALT-ENTRY under H1 + refresh-fail. Sprint 31.94
  reconnect-event consumer is the ultimate fix.

- **NEW RSK-FAI-COMPLETENESS (Tier 3 verdict 2026-04-29):** FAI's
  self-falsifiability clause triggered during Phase A Tier 3 (entry #9
  added). Pattern of recurring FAI misses (Round 1 asyncio yield-gap +
  Round 2 ib_async cache freshness + Phase A Tier 3 callback-path
  bookkeeping atomicity = three primitive-semantics misses) suggests Round
  3 may surface a fourth. Severity: **MEDIUM** (mitigation in-sprint;
  bounded by Round 3 cycle). Mitigation: Phase B/C re-run + Round 3
  full-scope cross-check; Round 3 escalation pre-commitment (Decision 7)
  bounds the worst-case revision pass count to one more.

- **NEW RSK-CROSS-LAYER-INCOMPLETENESS (Tier 3 verdict 2026-04-29):**
  Cross-layer composition test count at 5 (above template floor; below
  exhaustive). DEC-386's empirical falsification justifies heightened
  bar; CL-6 explicitly deferred per Decision 5. Severity: **MEDIUM**
  (DEC-386's empirical falsification establishes precedent; Sprint 31.92's
  5-test commitment closes most operationally-relevant compositions).
  Mitigation: 5 tests committed; CL-6 deferral rationale documented in
  `docs/process-evolution.md`; future cross-layer claims subject to same
  protocol requirement.

- **RSK-PHASE-A-TIER-3-DEFERRED — NOT FILED.** This Tier 3 occurred
  2026-04-29.

- **RSK-022 (Sprint 21.6)** — IBKR Gateway nightly resets. Sprint 31.92
  does NOT introduce new dependencies on Gateway uptime; Path #2's
  locate-rejection detection IS Gateway-uptime-independent.

## Falsifiable Assumption Inventory

Reproduced verbatim from `falsifiable-assumption-inventory.md` (revised
9-entry inventory). The Phase A Tier 3 review #1 (2026-04-29) exercised
the inventory's self-falsifiability clause once (entry #9 added). Round 3
full-scope cross-check is the next defense layer.

| # | Primitive-semantics assumption | Falsifying spike or test | Status |
|---|--------------------------------|--------------------------|--------|
| 1 | asyncio guarantees that synchronous Python statements between two `await` points (or in a coroutine body without any `await`) execute atomically with respect to other coroutines on the same event loop. The C-1 reservation pattern's correctness depends on `_reserve_pending_or_fail`'s body remaining synchronous post-refactor (no `await` between ceiling-check and reserve increment). **NOTE:** entry #9 extends this assumption to all callback paths that mutate the bookkeeping counters; entry #1 covers the place-time emit path specifically. | (a) AST-level scan asserts no `ast.Await` node within `_reserve_pending_or_fail`'s body. (b) Mocked-await injection test: monkey-patch implementation to insert `await asyncio.sleep(0)` between check and reserve, assert the race IS observable under injection. | **unverified — falsifying spike scheduled in S4a-i.** |
| 2 | `ib_async`'s position cache catches up to broker state within `Broker.refresh_positions(timeout_seconds=5.0)` under all observed reconnect-window conditions. AC2.5's refresh-then-verify mechanism's correctness depends on this. **High-volume steady-state behavior is OUT of Sprint 31.92 scope per Tier 3 item D / Decision 5 / DEF-FAI-2-SCOPE — deferred to Sprint 31.94.** | S3b sub-spike measures `cache_staleness_p95_ms`, `cache_staleness_max_ms`, `refresh_success_rate`, `refresh_p95_ms` across N≥10 reconnect cycles. Halt gate: `cache_staleness_max_ms > refresh_timeout_seconds × 1000` halts. Branch 4 (`verification_stale: true`) is the structural defense if non-convergent. **`SimulatedBrokerWithRefreshTimeout` fixture (S5c) enables in-process Branch 4 unit testing per Tier 3 item E / DEF-SIM-BROKER-TIMEOUT-FIXTURE.** | **unverified — falsifying spike scheduled in S3b; Branch 4 + S5c fixture are load-bearing defenses.** |
| 3 | IBKR's `modifyOrder` rejection rate is stable at ≤5% steady-state AND remains stable under adversarial conditions. The H2 mechanism selection's correctness depends on the determinism claim, NOT just the steady-state rate. | S1a adversarial sub-spike per Decision 1: (i) concurrent amends across N≥3 positions, (ii) amends during reconnect window, (iii) amends with stale order IDs. Halt gate uses worst-axis Wilson UB. JSON gains `adversarial_axes_results`, `worst_axis_wilson_ub`. | **unverified — falsifying spike scheduled in S1a.** |
| 4 | The S1b substring fingerprint catches every variant of the locate-rejection error string IBKR can produce. AC2.1's case-B detection's correctness depends on this. | S1b substring-fingerprint validation across ≥5 symbols × ≥10 trials. Sampling bounded to single account/version/configuration. | **measured-only — acceptable because Decision 4 auto-activates AC2.7 watchdog on first observed `case_a_in_production` event.** |
| 5 | `cancel_all_orders(symbol, await_propagation=True)` synchronously confirms all bracket-child cancellations broker-side before returning. The H1 fallback path's correctness depends on this. | S1a strengthened cancel-then-immediate-SELL stress per Decision 2: N=100 trials, ≤10ms gap. **HARD GATE: any 1 conflict in 100 → H1 NOT eligible regardless of `modifyOrder` Wilson UB.** JSON gains `h1_propagation_n_trials=100`, `h1_propagation_zero_conflict_in_100: bool`. | **unverified — falsifying spike scheduled in S1a.** |
| 6 | IBKR raises a locate-rejection exception (case B) on hard-to-borrow symbols rather than silently holding the order pending borrow (case A). | S1b explicit case-A vs case-B differentiation per M-R2-1. JSON: `case_a_observed: bool`, `case_a_count: int`, `case_b_count: int`, `case_a_max_age_seconds: int`. Decision 4 auto-activation on first `case_a_in_production`. | **unverified — falsifying spike scheduled in S1b.** |
| 7 | `on_position_closed` event fires on all four ARGUS position-close paths. AC2.6's suppression-dict-clear mechanism's correctness depends on this. | M-R2-2 regression test exercises all four close paths and asserts the dict entry is cleared in each. | **unverified — falsifying spike scheduled in S3b.** |
| 8 | The H-R2-5 codebase scan for `is_stop_replacement=True` callers (Regression Checklist invariant 24) has no false-negative paths via reflective or aliased call patterns. | S4a-ii adversarial regression sub-tests per Decision 3 / option (a): (a) `**kw` unpacking; (b) computed-value flag assignment; (c) `getattr` reflective access. Option (b) accept-and-document NOT taken. | **unverified — falsifying spike scheduled in S4a-ii.** |
| 9 | **(NEW per Tier 3 item A — callback-path bookkeeping atomicity.)** All bookkeeping update paths on `cumulative_pending_sell_shares` and `cumulative_sold_shares` execute synchronously between read and write. The L3 ceiling correctness depends on the asyncio single-event-loop guarantee applying to every path that mutates these counters, not only `_reserve_pending_or_fail`. | S4a-ii AST-no-await scan + mocked-await injection regression extended to `_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, AND the `_check_sell_ceiling` multi-attribute read sequence per Tier 3 items A + B / DEF-FAI-CALLBACK-ATOMICITY. | **unverified — falsifying spike scheduled in S4a-ii. Sprint-gating Round 3 advancement.** |

**Self-falsifiability clause (preserved load-bearing):** Per
`templates/sprint-spec.md` v1.2.0 § Falsifiable Assumption Inventory, this
inventory is itself a falsifiable artifact. **If Round 3 (or any
subsequent review) finds an additional primitive-semantics assumption
load-bearing on the proposed mechanism not in this list, the inventory
has failed — and the mechanism's adversarial-review verdict must be
downgraded accordingly.** Phase A Tier 3 already exercised this clause
once (entry #9 added 2026-04-29); Round 3 full-scope cross-check is the
next defense layer. Decision 7 (operator pre-commitment) binds the
response: a primitive-semantics-class Critical in Round 3 routes to
another revision pass (Phase A re-entry per Outcome C); any other
Critical class routes to RSK-and-ship.

## Hypothesis Prescription

This sprint's first two sessions (S1a + S1b) are diagnostic phases. The
symptoms (Path #1 over-flatten, Path #2 retry storm) are reproducible from
the Apr 28 trace data. The spec author's primary hypothesis is **H2
(amend-stop-price) for Path #1** — this is the safety-justified default
given AMD-2's original engineering rationale. H4 hybrid is the choice if
H2 alone has unreliable rejection rates; **H1 cancel-and-await is the
LAST-RESORT fallback** if both H2 and H4 are empirically infeasible. For
Path #2, H5 (substring fingerprint stability) and H6 (suppression-window
calibration on hard-to-borrow microcaps) are the empirical questions.

| ID | Hypothesis | Confirms-if | Rules-out-if | Spec-prescribed fix shape |
|----|-----------|-------------|--------------|---------------------------|
| H2 (Path #1, **PRIMARY DEFAULT**) | Amend-stop-price via `modifyOrder` is the correct mechanism: trail stop / emergency flatten amend the bracket stop's `auxPrice` rather than placing a new market SELL, eliminating the second-SELL race entirely. AMD-2 invariant preserved; DEC-117 atomic-bracket invariant preserved; zero unprotected window. | S1a measures `modifyOrder` round-trip latency ≤ 50ms p95 AND **worst-axis Wilson UB on rejection rate < 5%** (per Decision 1 — adversarial axes (i) concurrent across N≥3 positions, (ii) reconnect-window, (iii) stale order IDs) AND deterministic propagation across ≥50 trials AND **`h1_propagation_zero_conflict_in_100 == true`** (per Decision 2 hard gate). | S1a observes worst-axis Wilson UB ≥5% on rejection rate OR non-deterministic acknowledgment OR amend doesn't actually update the IBKR-side bracket stop in some trials. | Amend bracket stop's `auxPrice` to trail-stop price; remove the trail-flatten market SELL emission. AMD-2 invariant PRESERVED. AC1.5 framing: "AMD-2 preserved." |
| H4 (Path #1, **FALLBACK if H2 is unreliable**) | Hybrid: try amend first, fall back to cancel-and-await on amend rejection. | S1a observes worst-axis Wilson UB on amend rejection rate 5%–20% AND `h1_propagation_zero_conflict_in_100 == true` (per Decision 2 hard gate). | S1a observes worst-axis Wilson UB <5% (use H2 alone) OR ≥20% (consider H1 alone). | Two-path implementation: amend first, fall back to cancel-and-await on amend rejection. Operator-audit logging on every fallback occurrence per AC1.6. AC1.5 framing: "AMD-2 preserved on amend-success path; superseded on cancel-fallback path." |
| H1 (Path #1, **LAST-RESORT FALLBACK only**) | Cancel-and-await before SELL. AMD-2 invariant superseded by AMD-2-prime (unprotected window bounded by `cancel_propagation_timeout` ≤ 2s). | (Activated only if H2 AND H4 both empirically infeasible AND `h1_propagation_zero_conflict_in_100 == true` per Decision 2 hard gate.) | (Implicit — H2 or H4 selected first.) **HARD GATE: if `h1_propagation_zero_conflict_in_100 == false` (any 1 conflict in 100 trials), H1 is NOT eligible regardless of `modifyOrder` Wilson UB.** | Cancel-and-await before SELL in `_trail_flatten`, `_resubmit_stop_with_retry` emergency path, and conditionally `_escalation_update_stop`. AMD-2 superseded; AC1.6 operator-audit logging mandatory; DEC-390 must explicitly call out H1 as last-resort with rationale. **C-R2-1↔H-R2-2 coupling per Tier 3 item C:** if H1 is the active mechanism AND `Broker.refresh_positions()` raises or times out, position marked `halt_entry_until_operator_ack=True`. |
| H3 (Path #1) | Recon-trusts-marker — accept the over-flatten as inevitable but mark `redundant_exit_observed = True` so reconciliation classifies as SAFE. | (Not validated in S1a — REJECTED at Phase A: requires `ManagedPosition.redundant_exit_observed` SQLite persistence which DEC-386 deferred to Sprint 35+ Learning Loop V2.) | (Implicit — already ruled out at Phase A.) | N/A — REJECTED. Listed for completeness in DEC-390 Context section. |
| H5 (Path #2) | The locate-rejection error string `"contract is not available for short sale"` is stable in current `ib_async` API and matches the substring exactly. | S1b's manual reproduction (force a SELL on each of ≥5 known hard-to-borrow microcap symbols during paper hours, ≥10 trials per symbol) captures the exact string in ALL trials. | S1b captures variant strings OR captures inconsistent strings depending on conditions. | Substring fingerprint helper as specified. If RULES-OUT, fingerprint becomes a regex or substring-list at S3a; impl prompt updated. |
| H6 (Path #2) | Suppression window calibrated to S1b spike's measured p99 hold-pending-borrow release window plus 20% margin is sufficient. | S1b observes ≥1 actual release event across the ≥5-symbol × ≥10-trial spike AND captures p95/p99 release timing per symbol class. Default `locate_suppression_seconds = max(p99 measurements across all symbols) × 1.2`, with hard floor at 18000s (5hr) and hard ceiling at 86400s (24hr). | S1b observes ZERO release events across all trials — held orders all timeout/cancel without filling. In this case, the suppression-timeout fallback (AC2.5 broker-verification) is the dominant code path and AC2.5's behavior is what matters most; default falls back to 18000s with documented rationale. | Default value baked into Pydantic field at code-generation time per AC2.5 + Config Changes table. If H6 RULED OUT (no releases observed), default = 18000s; AC2.5 broker-verification path receives extra emphasis in S5b validation. |

**Required halt-or-proceed gate language (H-R2-2-tightened, verbatim into
S2a + S2b + S3a + S3b implementation prompts, per protocol §"Hypothesis
Prescription"):**

> Compute Wilson UB from observed rejection rate AS WELL AS the
> cancel-then-immediate-SELL stress sub-spike outcomes. **Decision rule
> (per Decision 2 — N=100 hard gate):** pick H2 if **worst-axis Wilson
> UB** (per Decision 1 — adversarial axes (i)/(ii)/(iii)) **< 5%** AND
> `h1_propagation_zero_conflict_in_100 == true`. Pick H4 if 5% ≤
> worst-axis Wilson UB < 20% AND `h1_propagation_zero_conflict_in_100 ==
> true`. Pick H1 ONLY IF `h1_propagation_zero_conflict_in_100 == true`
> AND worst-axis Wilson UB ≥ 20% AND operator confirms H1 selection in
> writing per existing tightened gate language. **HARD GATE: if even 1
> trial in 100 exhibits a conflict (`h1_propagation_zero_conflict_in_100
> == false`), H1 is NOT eligible regardless of Wilson UB; surface to
> operator with explicit "H1 unsafe" determination and require alternative
> architectural fix (likely Sprint 31.94 D3 or earlier).** If findings are
> inconclusive or fall outside the enumerated hypotheses, HALT and write
> the diagnostic findings file with status INCONCLUSIVE; surface to
> operator before proceeding. Do NOT ship a Phase B fix that doesn't
> address the Phase A finding. **The hierarchy is H2 > H4 > H1 — safety
> drives the order, not operator preference.**

The escape-hatch language is load-bearing. The implementing session is
explicitly authorized to deviate from the spec-prescribed fix shape when
the diagnostic finding warrants it, provided the deviation is called out
in the close-out's "Judgment Calls" section with cross-reference to the
spike artifact under
`scripts/spike-results/spike-def204-round2-{path1,path2}-results.json`.

## Session Count Estimate

**13 sessions** (was 10 pre-Tier-3; +3 per Phase B re-run): 2 spike
sessions (S1a + S1b — no production code changes; output JSON artifacts) +
8 implementation/validation sessions (S2a + S2b + S3a + S3b + S4a-i +
S4b + S5a + S5b) + 2 NEW sessions (S4a-ii callback-path atomicity per
Tier 3 items A + B + Decision 3; S5c cross-layer composition tests +
`SimulatedBrokerWithRefreshTimeout` fixture per Decision 5 + Tier 3 item
E) + 1 mid-sprint Tier 3 review event (M-R2-5, between S4a-ii and S4b).

Compaction-risk re-validation per `protocols/sprint-planning.md` v1.3.0 §
Phase A step 5: every session post-mitigation scores ≤13.5 (Medium). Zero
sessions at compaction score 14+. Detailed scoring tables for all 13
sessions are in `session-breakdown.md`.

**Net pytest target:** 88–114 new logical tests (was 75–95 pre-Phase-B-re-run);
~108–134 effective with parametrize multipliers. Final test-count target:
**5,357–5,403 pytest** (5,269 baseline + 88–134 new), 913 Vitest unchanged
(zero UI changes per frontend immutability invariant).

**Cumulative diff bound on `argus/execution/order_manager.py`:**
recalibrated to **~1150–1300 LOC** (was ~1100–1200 LOC pre-Tier-3) per
Tier 3 guidance, accommodating callback-path AST guards (S4a-ii) + Branch
4 coupling (S3b per Tier 3 item C) + AC2.7 auto-activation (Decision 4)
+ `halt_entry_until_operator_ack` field threading.

No frontend visual review (zero UI changes) — no contingency budget for
visual-review fixes.

**Round 3 verdict pending.** Round 3 is full scope per Outcome C; verdict
routes per Decision 7 binding pre-commitment (verbatim in
`escalation-criteria.md` § Round 3 Outcome Pre-Commitment).
