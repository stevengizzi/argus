# Sprint 31.92 — Tier 2 Review Context

> **Phase D artifact (shared).** This is the single backing file referenced
> by every Tier 2 session review prompt in Sprint 31.92. It contains the
> full Sprint Spec, Specification by Contradiction, Sprint-Level Regression
> Checklist, and Sprint-Level Escalation Criteria embedded inline so the
> @reviewer subagent can read this one file plus the session close-out and
> have everything needed to verdict.
>
> **Do NOT modify this file during sprint execution.** It freezes the
> Phase C re-sealed (post-Round-3) artifact set as of HEAD commit
> `08052b2` + S5c score correction `ff945c8`. If a session discovers a
> spec gap, file the discovery in the work-journal conversation, not here.
>
> **Sprint:** 31.92 — DEF-204 Round 2 (concurrent-trigger race + locate-rejection retry storm + long-only SELL-volume ceiling + DEF-212 constant drift wiring).
> **Predecessor:** Sprint 31.91 (sealed 2026-04-28) + Sprint 31.915 (sealed 2026-04-28).
> **Sessions (12 implementation + 1 review event):** s1a, s1b, s2a, s2b, s3a, s3b, s4a-i, s4a-ii, [M-R2-5 mid-sprint Tier 3 review event], s4b, s5a, s5b, s5c.
> **Mode:** Human-in-the-loop. Working on `main`.
> **Mitigation in effect:** Operator runs `scripts/ibkr_close_all_positions.py` daily until cessation criterion #5 (5 paper sessions clean post-31.92 seal) is satisfied.
> **Tier 3 review:** M-R2-5 fires between S4a-ii close-out and S4b start (architectural-closure cross-check; PROCEED → continue / REVISE_PLAN → halt / PAUSE_AND_INVESTIGATE → halt).

---

## Review Instructions

You are conducting a Tier 2 code review for one session of Sprint 31.92.

**This is a READ-ONLY session.** Do NOT modify any source code files. The
ONE permitted write is the review report file itself
(`docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-{session-id}-review.md`),
including a structured JSON verdict appendix fenced with
` ```json:structured-verdict ` per the review skill.

Follow the review skill in `.claude/skills/review.md`.

**Read `.claude/rules/universal.md` in full and treat its contents as
binding for this review.** RULE-013 (read-only mode) governs the
entire review session. RULE-038 (grep-verify discipline), RULE-050 (CI
green), RULE-051 (mechanism signature vs symptom aggregate validation),
and RULE-053 (architectural-seal verification) are particularly relevant
for this CRITICAL safety sprint.

**Your verdict must be one of:**
- `CLEAR` — proceed to next session.
- `CONCERNS` — medium issues that need triage. The implementation session
  may iterate within itself per the Post-Review Fix Documentation pattern;
  if so, the verdict transitions to `CONCERNS_RESOLVED` after fixes land.
- `ESCALATE` — requires operator. Do NOT fix without human review.

The implementation prompt's @reviewer invocation at session-end provides:
1. This review context file
2. The session close-out report path
3. The diff range (`git diff HEAD~1` typically)
4. The test command to run
5. The list of files that should NOT have been modified

**Critical sprint-wide invariants — verify on every session:**
1. `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b SAFE-marker path) — preserve verbatim.
2. `argus/execution/order_manager.py::reconcile_positions` Pass 1 startup branch + Pass 2 EOD branch (DEC-385 L3 + L5) — preserve verbatim.
3. `argus/execution/order_manager.py::_check_flatten_pending_timeouts` 3-branch side-check at lines ~3424–3489 (DEF-158 fix anchor `a11c001`) — preserve verbatim.
4. `argus/main.py::check_startup_position_invariant` and `_startup_flatten_disabled` flag (Sprint 31.94 D2 surfaces) — zero edits.
5. `argus/main.py:1081` (`reconstruct_from_broker()` call site, Sprint 31.94 D1 surface) — zero edits EXCEPT S4b's `OrderManager(...)` construction-site amendment + `--allow-rollback` CLI flag parsing.
6. `argus/execution/order_manager.py::reconstruct_from_broker` body — zero edits BEYOND the single-line `position.is_reconstructed = True` addition per AC3.7.
7. Pre-existing 5,269 pytest baseline holds; new tests are additive only.
8. Pre-existing flake count (DEF-150, DEF-167, DEF-171, DEF-190, DEF-192) does not regress (RULE-041).
9. CI must be green on the session's final commit (RULE-050).
10. Frontend immutability: `git diff <session-base>..HEAD -- 'frontend/'` returns empty; Vitest count stays at 913.

The full 34-invariant list is embedded below as the
**Sprint-Level Regression Checklist**.

---

# Embedded: Sprint Spec

> Source: `sprint-spec.md` (Phase C re-sealed, 2026-04-29).

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
   `IBKRBroker.refresh_positions()` body uses single-flight `asyncio.Lock` +
   250ms coalesce window per Round 3 C-R3-1 disposition. Concurrent callers
   serialized; rapid-succession callers benefit from coalesce.

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
  safety preserved). `now` is `time.monotonic()` per Round 3 H-R3-1 —
  suppression-timeout comparisons are wall-clock-skew-resilient.
- **AC2.3:** Locate-rejection at any of the 4 standalone-SELL paths
  triggers suppression-dict entry: `_locate_suppressed_until[position.id]
  = time.monotonic() + config.locate_suppression_seconds` (per Round 3
  H-R3-1 — applies at all 4 standalone-SELL exception handlers).
- **AC2.4:** Subsequent SELL emit attempts at the same `ManagedPosition.id`
  during the suppression window are skipped (no broker call). Other
  `ManagedPosition`s on the same symbol are NOT affected (cross-position
  safety per Round-1 H-2).
- **AC2.5 (broker-verified suppression-timeout fallback — three branches +
  Branch 4 + HALT-ENTRY coupling per Tier 3 item C):**
  - Suppression-timeout fallback FIRST calls
    `await self._broker.refresh_positions(timeout_seconds=5.0)` (new ABC
    method per C-R2-1). `refresh_positions()` is single-flight serialized
    per Round 3 C-R3-1 disposition; the timeout still applies (5s per call);
    concurrent callers either await the lock (within their own 5s budget)
    or coalesce on the prior caller's synchronization (250ms window).
  - **Branch 4 (`verification_stale: true`):** if `refresh_positions`
    raises or times out, publish `phantom_short_retry_blocked` alert with
    metadata `{verification_stale: True, verification_failure_reason:
    type(exc).__name__, position_id, symbol}`. **C-R2-1↔H-R2-2 coupling
    per Tier 3 item C:** if H1 is the active mechanism AND Branch 4 fires,
    additionally mark position `halt_entry_until_operator_ack=True`. No
    further SELL attempts on the position; no phantom short. Operator-driven
    resolution.
  - **Branch 4 throttle per Round 3 M-R3-2:** Branch 4 firings on the same
    `ManagedPosition.id` within a session are throttled to one per hour at
    alert layer (first firing publishes; subsequent within 1 hour are
    suppressed at alert layer with INFO log entry `branch_4_throttled:
    true`); HALT-ENTRY effect persists; throttle resets on
    `on_position_closed` or successful refresh observation.
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
  auto-activation; per Round 3 H-R3-2 amended for storage / event-definition
  / atomicity / logged-transition semantics):** Watchdog monitors per-position
  pending-SELL age; fires when `now - position.last_sell_emit_time >
  pending_sell_age_seconds` AND no fill observed. Activated via config
  field `order_management.pending_sell_age_watchdog_enabled` with values
  `auto` (default) / `enabled` / `disabled`. **`auto` mode flips to
  `enabled` on first observed `case_a_in_production` event** in production
  paper trading. NOT manual operator activation per Decision 4. Provides
  the structural fallback for any unmodeled locate-rejection string variant
  (FAI #4 mitigation).
  - **Storage (per H-R3-2):** in-memory Pydantic field mutation only; no
    persistence; restart resets to `auto`.
  - **Event-definition (per H-R3-2):** "first observed `case_a_in_production`"
    is globally-scoped, single ARGUS process lifetime, defined as: first
    time `_pending_sell_age_seconds` exceeds threshold AND no fill observed
    AND `_locate_suppressed_until[position.id]` is set, in any position.
  - **Atomicity (per H-R3-2):** flip guarded by `asyncio.Lock` in watchdog
    detection path; re-entrant flips are no-ops (idempotent).
  - **Logged transition (per H-R3-2):** structured log line
    `event="watchdog_auto_to_enabled"` on flip with `case_a_evidence:
    {position_id, symbol, age_seconds_at_flip}`.
- **AC2.8 (NEW per Round 3 H-R3-3 — `halt_entry_until_operator_ack`
  consumer + ack mechanism + restart behavior + logged transitions):**
  - **Consumer:** RiskManager Check 0 (existing DEC-027) is extended to
    also reject entries when ANY ManagedPosition has
    `halt_entry_until_operator_ack=True` AND the entry signal is for the
    SAME `ManagedPosition.id`. Per-position granularity preserved; new
    positions on the same symbol unaffected.
  - **Ack mechanism:** new REST endpoint
    `POST /api/v1/positions/{position_id}/clear_halt` + new CLI tool
    `scripts/clear_position_halt.py {position_id}`. No Web UI changes
    (per SbC §13).
  - **Restart behavior:** halt-entry flag does NOT survive restart; the
    `is_reconstructed=True` posture (AC3.7) subsumes halt-entry by
    refusing ALL ARGUS-emitted SELLs on reconstructed positions.
  - **Logged transitions:** `event="halt_entry_set"` on Branch 4 + H1
    firing; `event="halt_entry_cleared"` on operator-ack via CLI/REST.

#### Deliverable 3 (Long-only SELL-volume ceiling — synchronous-update invariant extended per Tier 3 items A + B)

- **AC3.1 (5 state transitions + synchronous-update invariant on ALL
  bookkeeping callback paths per Tier 3 items A + B; the synchronous-update
  invariant scope is enforced by FAI #11 exhaustiveness regression at
  S4a-ii per Round 3 H-R3-5):** Pending-reservation
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
- **AC3.5 (canonical C-1 race test + AST guards per Tier 3 items A + B;
  callsite-enumeration exhaustiveness per Round 3 H-R3-5 / FAI #11):**
  Two coroutines on same `ManagedPosition` both attempt SELL emission;
  first passes ceiling and increments pending; second sees pending and
  FAILS ceiling check; refuses SELL. Plus AST-no-await scan + mocked-await
  injection regression on `_reserve_pending_or_fail` (S4a-i) AND on all 5
  bookkeeping callback paths (S4a-ii per FAI entry #9). Plus
  `test_bookkeeping_callsite_enumeration_exhaustive` at S4a-ii per FAI #11
  — AST scan walks `OrderManager`'s source for `ast.AugAssign` nodes
  targeting `cumulative_pending_sell_shares` or `cumulative_sold_shares`,
  finds the enclosing function name for each, and asserts the set of
  enclosing functions is a subset of the FAI #9 protected callsite list.
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
- **AC4.6 (dual-channel CRITICAL warning — H-R2-4 combined; extended
  per Round 3 H-R3-4 with interactive ack + periodic re-ack +
  CI-override flag separation):** When
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
  - **Startup-time interactive ack per H-R3-4** (default ON for non-CI
    environments): when `bracket_oca_type != 1` AND `--allow-rollback`
    AND interactive TTY detected, ARGUS prompts for the exact phrase
    "I ACKNOWLEDGE ROLLBACK ACTIVE"; anything else exits with code 3.
  - **Periodic re-ack per H-R3-4:** every 4 hours during runtime, ntfy.sh
    `system_warning` urgent + canonical-logger CRITICAL with phrase
    "DEC-386 ROLLBACK ACTIVE — STILL IN ROLLBACK STATE — N hours since
    startup".
  - **CI override flag per H-R3-4:** `--allow-rollback-skip-confirm`
    (separate from `--allow-rollback`) bypasses the interactive prompt
    for unattended starts. Both flags required for CI use.
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
- **AC5.6 (Cross-Layer Composition Tests committed at S5c per Decision 5;
  extended to 6 tests per Round 3 C-R3-1 — CL-7 added):**
  All 6 cross-layer composition tests (CL-1 through CL-5 + CL-7; see § "Defense-in-Depth
  Cross-Layer Composition Tests" below) committed in
  `tests/integration/test_def204_round2_validation.py`.
  `tests/integration/conftest_refresh_timeout.py` provides the
  `SimulatedBrokerWithRefreshTimeout` fixture variant (DEF-SIM-BROKER-TIMEOUT-FIXTURE)
  enabling in-process Branch 4 testing for CL-3 + a dedicated Branch 4
  unit test. **CL-7 (concurrent-caller correlation; per Round 3 C-R3-1):**
  N=2 concurrent AC2.5 fallbacks, broker state mutated between callers,
  assert no stale Branch 2 classification.

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
**Sprint 31.92 commits to 6 cross-layer composition tests post-Round-3
C-R3-1** (above the template's "at least one" floor; above Tier 3
sub-area D's 3-test floor; CL-7 added per Round 3 disposition)
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
- **CL-7 (concurrent-caller correlation; NEW per Round 3 C-R3-1):** N=2
  concurrent AC2.5 fallbacks (two coroutines each invoking
  `Broker.refresh_positions()` near-simultaneously; ≤10ms separation),
  broker state mutated between callers (e.g., position quantity changes
  between A's `reqPositions` and B's `reqPositions` via test-fixture
  injection); assert no stale Branch 2 classification — the single-flight
  serialization + 250ms coalesce window per Fix A guarantees coroutine B
  either awaits A's lock or coalesces on A's synchronization rather than
  reading a partially-converged cache. Falsifies if assertion holds
  WITHOUT the serialization mitigation (race observable) but holds WITH
  the mitigation.

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
| `Broker.refresh_positions()` single-flight serialization overhead (per Round 3 C-R3-1) | ≤ 1ms p95 (lock acquisition + coalesce-window check) | S3b benchmark — serialized callers measured against unserialized baseline; N=100 concurrent invocations |
| Helper `_read_positions_post_refresh()` per-call overhead (per Round 3 M-R3-4) | ≤ 5µs | S3b benchmark — synchronous helper composing `refresh_positions` then `get_positions` |
| Full-suite test runtime regression | ≤ +50s vs baseline 5,269 pytest (recalibrated per Tier 3 cumulative diff bound) | DEC-328 final-review full-suite measurement |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default | Validator |
|-----------|---------------|------------|---------|-----------|
| `order_manager.locate_suppression_seconds` | `OrderManagerConfig` | `locate_suppression_seconds` | **TBD-from-S1b spike (target p99+20%, likely 18000s = 5hr)** | `Field(default=<spike_value>, ge=300, le=86400)`. **Footnote per Round 3 H-R3-1:** Validator bounds (300–86400) are seconds in monotonic time per H-R3-1; equivalent to wall-clock under normal operation. |
| `order_manager.long_only_sell_ceiling_enabled` | `OrderManagerConfig` | `long_only_sell_ceiling_enabled` | `True` (fail-closed) | `Field(default=True)` |
| `order_manager.long_only_sell_ceiling_alert_on_violation` | `OrderManagerConfig` | `long_only_sell_ceiling_alert_on_violation` | `True` | `Field(default=True)` |
| `order_management.pending_sell_age_watchdog_enabled` | `OrderManagerConfig` | `pending_sell_age_watchdog_enabled` | `"auto"` | `Field(default="auto")` with `Literal["auto", "enabled", "disabled"]` validator. **NEW per Decision 4** — `auto` mode flips to `enabled` on first observed `case_a_in_production` event. **Storage per Round 3 H-R3-2:** in-memory only; auto→enabled flip is `asyncio.Lock`-guarded; restart resets to `auto`. |
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
> (per Decision 2 — N=100 hard gate; per Round 3 M-R3-1 — worst-axis
> across 4 adversarial axes):** pick H2 if **worst-axis Wilson UB**
> (per Decision 1 + Round 3 M-R3-1 — adversarial axes (i)/(ii)/(iii) +
> NEW axis (iv) joint reconnect+concurrent: concurrent amends across
> N≥3 positions DURING reconnect window) **< 5%** AND
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

**Net pytest target:** 95–121 new logical tests (was 88–114 pre-Round-3;
recalibrated per Round 3 disposition aggregate row — ~7–11 net new tests
for C-R3-1 + 4 High findings); ~115–145 effective with parametrize
multipliers. Final test-count target: **5,364–5,414 pytest** (5,269
baseline + 95–145 new), 913 Vitest unchanged (zero UI changes per
frontend immutability invariant).

**Cumulative diff bound on `argus/execution/order_manager.py`:**
recalibrated to **~1200–1350 LOC** (was ~1150–1300 LOC pre-Round-3; per
Round 3 disposition aggregate row), accommodating callback-path AST
guards (S4a-ii) + Branch 4 coupling (S3b per Tier 3 item C) + AC2.7
auto-activation (Decision 4) + `halt_entry_until_operator_ack` field
threading + `_read_positions_post_refresh()` helper (per Round 3 M-R3-4)
+ Branch 4 throttle (per Round 3 M-R3-2) + AC2.8 ack-clear logged
transitions (per Round 3 H-R3-3).

**NEW cumulative diff bounds per Round 3 disposition (additional files):**
- `argus/execution/ibkr_broker.py`: ~30–50 LOC for the single-flight
  serialization wrapper (`asyncio.Lock` + 250ms coalesce window) per
  Round 3 C-R3-1.
- `argus/risk/risk_manager.py`: ~20 LOC for the halt-entry Check 0
  extension per Round 3 H-R3-3.
- `argus/api/v1/positions.py` (NEW file): ~30 LOC for the halt-clear
  REST endpoint per Round 3 H-R3-3.
- `scripts/clear_position_halt.py` (NEW file): ~20 LOC for the operator
  CLI tool per Round 3 H-R3-3.
- `argus/main.py`: ~30 LOC for the interactive ack at startup +
  periodic re-ack loop + `--allow-rollback-skip-confirm` CI override
  flag parsing per Round 3 H-R3-4.

No frontend visual review (zero UI changes) — no contingency budget for
visual-review fixes.

**Sprint Abort Condition (NEW per Round 3 C-R3-1):** If Fix A
serialization spike (S3b sub-spike for FAI #10) fails AND no alternative
serialization design surfaces, sprint halts; operator decides whether to
escalate to Phase A re-entry retroactively. (Materialized as a new entry
in `escalation-criteria.md` § Sprint Abort Conditions at Phase D prompt
generation.)

**Round 3 verdict pending.** Round 3 is full scope per Outcome C; verdict
routes per Decision 7 binding pre-commitment (verbatim in
`escalation-criteria.md` § Round 3 Outcome Pre-Commitment).

---

# Embedded: Specification by Contradiction

> Source: `spec-by-contradiction.md` (Phase C re-sealed, 2026-04-29).

# Sprint 31.92: What This Sprint Does NOT Do

> **Phase C artifact 4/9 (revised post-Tier-3 + Phase B re-run, 2026-04-29).**
> Defines the boundaries of Sprint 31.92 — DEF-204 Round 2. Prevents scope
> creep during implementation; gives the Round 3 reviewer (full scope per
> Outcome C) and Tier 2 reviewer (per-session) clear boundaries to check.
> Sprint 31.91 Tier 3 #1 explicitly flagged scope creep as a concern; this
> document is the structural defense against that pattern recurring.
>
> **Revision history:**
> - Round 1 authored 2026-04-28 (original Edge Case #1 framing of asyncio
>   serialization was structurally wrong).
> - Round-1-revised 2026-04-29: incorporated adversarial findings C-1 (Edge
>   Case #1 corrected), C-2 (new Out of Scope #20–#21 rejecting
>   reviewer's `data/argus.db` reconstruction option + DEF-209 forward-pull),
>   H-1 (new Edge Case #15 rejecting ceiling check at bracket placement),
>   H-3 (Edge Case #5 updated for broker-verification mitigation), H-4 (new
>   Out of Scope #22 rejecting `bracket_oca_type` Pydantic validator
>   restriction).
> - Round-2-revised 2026-04-29: incorporated L-R2-1 rephrasing of #20/#21
>   from "definitively impossible" framing to "judgment call" framing per
>   `templates/spec-by-contradiction.md` v1.1.0 § Rejecting Adversarial-
>   Review-Proposed Alternatives.
> - **This Phase C revision 2026-04-29:** added new Out-of-Scope items
>   #24 (CL-6 cross-layer test deferral per Decision 5), #25 (FAI #2
>   high-volume axis per Tier 3 item D / DEF-FAI-2-SCOPE), #26 (Sprint
>   31.94 D3 prioritization per Decision 6). Updated Edge Case #1 to
>   acknowledge the broader synchronous-update invariant scope per Tier 3
>   item A + FAI entry #9. Added new Edge Case #18 for Branch 4
>   refresh-failure semantics per Tier 3 item C / C-R2-1↔H-R2-2 coupling.
>   Pre-existing rephrasings preserved.

The sprint focuses narrowly on closing the two empirically-falsifying
paths from the 2026-04-28 paper-session debrief, plus a structural
ceiling with concurrency-safe pending reservation as defense-in-depth
(extended per Tier 3 entry #9 to all bookkeeping callback paths), plus
the DEF-212 rider with operator-visible rollback gate. Everything else
— even items thematically adjacent to safety, reconciliation, or
order-management hygiene — is explicitly out of scope.

---

## Out of Scope

These items are related to the sprint goal but are explicitly excluded:

1. **Structural refactor of `_flatten_position`, `_trail_flatten`,
   `_escalation_update_stop`, or `_check_flatten_pending_timeouts` beyond
   the explicit safety properties enumerated in AC1–AC4.** These four
   functions are touched by 8 of the 13 sessions (S2a/S2b/S3a/S3b/S4a-i/S4a-ii/S4b
   indirectly via construction surface/S5c via cross-layer composition) —
   that's a maximum-overlap zone. The temptation to "while I'm in there,
   also fix X" must be resisted. Structural cleanup is Sprint 31.93
   component-ownership scope.

2. **Modifications to DEC-386's 4-layer OCA architecture (Sessions
   0/1a/1b/1c).** Specifically: `Broker.cancel_all_orders(symbol, *,
   await_propagation)` ABC contract, `IBKRBroker.place_bracket_order`
   OCA threading, `ManagedPosition.oca_group_id`, `_handle_oca_already_filled`,
   `# OCA-EXEMPT:` exemption mechanism, `reconstruct_from_broker()`
   STARTUP-ONLY docstring. All preserved byte-for-byte (regression
   invariant R6). Sprint 31.92 ADDS to this architecture (amend-stop-price
   OR cancel-and-await on Path #1; pending+sold ceiling on AC4); it does
   NOT modify the existing layers. The existing `bracket_oca_type=0`
   rollback escape hatch is PRESERVED — Sprint 31.92 does NOT remove the
   rollback option, only adds a startup CRITICAL warning per AC4.6 + a
   `--allow-rollback` CLI gate per AC4.7 when the operator deliberately
   enables it.

3. **Modifications to DEC-385's 6-layer side-aware reconciliation
   contract.** Specifically: `reconcile_positions()` Pass 1 startup
   branch + Pass 2 EOD branch, `phantom_short_gated_symbols` audit table,
   DEF-158 retry 3-branch side-check, `phantom_short_retry_blocked` alert
   path. Path #2's broker-verified suppression-timeout fallback REUSES
   the existing `phantom_short_retry_blocked` alert type — it does NOT
   introduce new behavior in DEC-385's surfaces. Branch 4
   (`verification_stale: true`) reuses the same emitter.

4. **Relocation of `_is_oca_already_filled_error` from
   `argus/execution/ibkr_broker.py` to `argus/execution/broker.py`.**
   Tier 3 #1 Concern A (Sprint 31.91, 2026-04-27) called for this
   relocation. Phase A explicitly DEFERRED it to Sprint 31.93
   component-ownership because (a) `broker.py` ABC modification is the
   natural home, (b) Sprint 31.92 already has 8 sessions touching
   `order_manager.py` and adding `broker.py` to the modify list expands
   blast radius unnecessarily, (c) the helper's current location is
   functionally correct — the relocation is cosmetic. **Note (Round-1
   reframing per L-R2-1):** this is a judgment call about scope phasing,
   not an empirical claim about location-correctness; subject to revisit
   if Sprint 31.93's actual scope shifts.

5. **DEF-211 D1+D2+D3 (Sprint 31.94 sprint-gating items).** Specifically:
   `ReconstructContext` enum + parameter threading on
   `reconstruct_from_broker()`, IMPROMPTU-04 startup invariant gate
   refactor, boot-time adoption-vs-flatten policy decision for broker-only
   LONG positions. RSK-DEC-386-DOCSTRING bound stays bound by Sprint 31.94.
   Sprint 31.92 must NOT touch `argus/main.py:1081` (the
   `reconstruct_from_broker()` call site) or `check_startup_position_invariant()`.
   The new `ManagedPosition.is_reconstructed: bool` flag (AC3.7) is set
   inside `reconstruct_from_broker()` itself — that single-line change
   inside the function body is in scope; the call site and surrounding
   `argus/main.py` infrastructure remain untouched.

6. **DEF-194/195/196 reconnect-recovery work (Sprint 31.94).**
   Specifically: IBKR `ib_async` stale position cache after reconnect,
   `max_concurrent_positions` divergence after disconnect-recovery,
   DEC-372 stop-retry-exhaustion cascade events. The 38 "Stop retry
   failed → Emergency flattening" events on Apr 28 are a Path #1 surface
   (covered by AC1.3's `_resubmit_stop_with_retry` emergency-flatten
   branch); the cluster-wide reconnect-recovery analysis is NOT in scope.
   **Specifically out: `IBKRReconnectedEvent` consumer that clears the
   locate-suppression dict.** That coupling is deferred to Sprint 31.94
   when the producer lands. AC2.5's broker-verification-at-timeout
   fallback (with new `Broker.refresh_positions()` ABC + Branch 4 +
   HALT-ENTRY coupling under H1+refresh-fail per Tier 3 item C) is the
   structural mitigation Sprint 31.92 ships in lieu of the consumer.

7. **`evaluation.db` 22GB bloat or VACUUM-on-startup behavior.** Sprint
   31.915 already merged DEC-389 retention + VACUUM. The Apr 28 debrief's
   secondary finding (eval.db forced premature shutdown) is closed.

8. **`ibkr_close_all_positions.py` post-run verification feature.** The
   Apr 28 debrief flagged this as a HIGH-severity DEF-231 candidate.
   Phase A retracted it: operator confirmed 2026-04-29 that the 43
   pre-existing shorts at boot were missed-run human error, NOT a script
   defect. The script does its job when run; building a verification
   harness around operator hygiene would not have caught the human-error
   case. NOT this sprint.

9. **The 4,700 broker-overflow routings noted in the Apr 28 debrief.**
   Debrief explicitly defers: "Possibly fine; possibly indicates
   `max_concurrent_positions` is too tight for the actual signal volume."
   Requires a separate analysis pass against `max_concurrent_positions:
   50` sizing. NOT a safety defect; out of scope.

10. **DEF-215 reconciliation-WARNING throttling.** Already DEFERRED with
    sharp revisit trigger ("≥10 consecutive cycles AFTER Sprint 31.91 has
    been sealed for ≥5 paper sessions"). Sprint 31.92 closure does not
    satisfy the trigger; DEF-215 stays deferred.

11. **Sprint 31B Research Console / Variant Factory work.** Conceptually
    adjacent but functionally orthogonal. Sequenced after 31.92 per Phase
    0 routing.

12. **Sprint 31.95 Alpaca retirement (DEF-178/183).** Wholly orthogonal
    scope.

13. **New alert observability features beyond a single `POLICY_TABLE`
    entry for `sell_ceiling_violation`.** Specifically out: `AlertBanner`
    UX changes, `AlertToastStack` queue capacity adjustments, new REST
    endpoints, new WebSocket event types, additional per-alert audit-trail
    enrichment. AC3.9 ADDS a single `POLICY_TABLE` entry
    (`operator_ack_required=True`, `auto_resolution_predicate=None`) and
    updates the AST exhaustiveness regression guard — that's the entire
    alert-system delta.

14. **Performance optimization beyond the explicit benchmarks in the
    Sprint Spec §"Performance Benchmarks".** AC's measure ≤50ms p95
    amend latency (H2), ≤200ms p95 cancel-and-await (H1 fallback),
    ≤10µs ceiling check, ≤5µs locate-suppression check, ≤5.2s p95
    broker-verification at timeout (worst-case slow path including
    `refresh_positions` round-trip per AC2.5), ≤1µs pending reservation
    arithmetic, ≤50s suite runtime regression. If any actual measurement
    exceeds these targets, halt and surface — do NOT optimize speculatively.

15. **Backporting AC1/AC2/AC3/AC4 fixes to Sprint 31.91-tagged code.**
    Sprint 31.92 lands at HEAD post-31.91-seal. There is no scenario where
    31.92's mechanism would be backported separately.

16. **Live trading enablement.** Sprint 31.91's cessation criterion #5
    (5 paper sessions clean post-seal) reset on Apr 28. Sprint 31.92's
    seal STARTS a new 5-session counter. Live trading remains gated by
    that counter PLUS Sprint 31.91 §D7's pre-live paper stress test under
    live-config simulation (DEF-208 — separately scoped).

17. **Documentation rewrites of `docs/architecture.md` §3.7 Order Manager
    beyond what AC's require.** AC-required: short subsection or paragraph
    about (a) Path #1 mechanism (H2 amend-stop-price default, H4 hybrid
    fallback, H1 last-resort), (b) `_is_locate_rejection` + position-keyed
    suppression dict + broker-verified timeout fallback (with new
    `Broker.refresh_positions()` ABC + Branch 4), (c)
    `cumulative_pending_sell_shares` + `cumulative_sold_shares` +
    `is_reconstructed` ceiling + `_pending_sell_age_watchdog_enabled`
    auto-activation, (d) `bracket_oca_type` flow from config to
    `OrderManager.__init__` + AC4.6 dual-channel CRITICAL warning + AC4.7
    `--allow-rollback` CLI gate. Anything beyond these four items is OUT.

18. **Restructuring or extending `SimulatedBroker` semantically.** S5a +
    S5b + S5c validation scripts may add NEW test fixtures (e.g.,
    `SimulatedBrokerWithLocateRejection`, `SimulatedBrokerWithRestartReplay`,
    **`SimulatedBrokerWithRefreshTimeout` per Tier 3 item E /
    DEF-SIM-BROKER-TIMEOUT-FIXTURE**) but must not modify SimulatedBroker's
    existing fill-model semantics, immediate-fill behavior, or OCA
    simulation. Existing tests pass without modification. **The fixture
    subclasses live in test files (`tests/integration/conftest_refresh_timeout.py`
    for `SimulatedBrokerWithRefreshTimeout`); production code in
    `argus/execution/simulated_broker.py` is unchanged.**

19. **Sprint-close cessation-criterion celebration.** Sprint 31.92
    sealing satisfies cessation criterion #4 (sprint sealed) for the new
    criterion-#5 counter — but criterion #5 itself (5 paper sessions
    clean post-Sprint-31.92 seal) starts at 0/5 again. Operator
    daily-flatten mitigation continues.

### Rejecting Adversarial-Review-Proposed Alternatives

Per `templates/spec-by-contradiction.md` v1.1.0 § Rejecting
Adversarial-Review-Proposed Alternatives, the following rejection
rationales must distinguish empirical falsification from judgment call.
All three Round-1-reviewer-proposed alternatives below are **judgment
calls**, not empirical falsifications, per L-R2-1 rephrasing
(2026-04-29).

20. **Reading `data/argus.db` trades table on startup to reconstruct
    `cumulative_sold_shares` for reconstructed positions.** Round-1
    reviewer's proposed option (a) for C-2. **REJECTED per L-R2-1
    judgment-call framing:** "Reviewer's proposed alternative was judged
    not worth the marginal complexity given that attribution of historical
    SELLs to specific reconstructed positions is ambiguous when there
    have been multiple sequential entries on the same symbol within a
    session — the trades table doesn't carry `ManagedPosition.id` linkage
    in a form that survives restart. NOT empirically falsified — the
    rejection is a judgment call subject to revisit if the trade-attribution
    cost shifts (e.g., if Sprint 35+ Learning Loop V2 adds the linkage as
    a side-effect of DEF-209 persistence)." The conservative
    `is_reconstructed = True` refusal posture (AC3.7) was chosen instead.
    Listed here so adversarial Round 3 reviewer sees the explicit
    rejection rationale rather than re-litigating.

21. **Persisting `cumulative_pending_sell_shares` or `cumulative_sold_shares`
    to SQLite (pulling DEF-209 forward).** Round-1 reviewer's proposed
    option (b) for C-2. **REJECTED per L-R2-1 judgment-call framing:**
    "Reviewer's proposed alternative was judged not worth the marginal
    complexity given that DEF-209 is a Sprint 35+ Learning Loop V2
    prerequisite covering broader field persistence (`Position.side`,
    `redundant_exit_observed`, and now the ceiling counters). Pulling
    forward would couple Sprint 31.92 to a 10+ sprint horizon. NOT
    empirically falsified — the rejection is a judgment call subject to
    revisit if the cost-benefit of forward-pull shifts." The
    `is_reconstructed` refusal posture removes the need for these
    counters to survive restart on reconstructed positions specifically.

22. **`bracket_oca_type` Pydantic validator restriction to literal `1`.**
    Round-1 reviewer's proposed option (a) for H-4. **REJECTED per
    L-R2-1 judgment-call framing:** "Reviewer's proposed alternative was
    judged not worth the marginal complexity given that DEC-386 explicitly
    designed the `bracket_oca_type=0` rollback escape hatch for emergency
    operator response. Removing the runtime-flippability would supersede
    DEC-386's design intent, which is out of Sprint 31.92's prerogative.
    NOT empirically falsified — the rejection is a judgment call subject
    to revisit if Sprint 31.94 reconnect-recovery work absorbs the
    rollback path." The dual-channel startup CRITICAL warning per AC4.6
    + `--allow-rollback` CLI gate per AC4.7 + `live-operations.md`
    documentation is the chosen mitigation.

23. **Re-running adversarial review on the original Round-1 spec.**
    Round 1 produced verdict Outcome B (3 Critical findings); revisions
    applied per `revision-rationale.md`. Round 2 reviewed the REVISED
    package. Round 2 produced 1C+5H+5M+3L; revisions applied per
    `round-2-disposition.md`. **Round 3 (current) reviews the
    Phase-C-revised package per Outcome C full scope** — not re-running
    Round 1 or Round 2 from scratch. Per Outcome C, Round 3 scope is
    full, not narrowed (the 2026-04-29 amendment supersedes Round 2
    disposition's narrowest-scope recommendation).

### NEW Out-of-Scope items per Tier 3 verdict + 7 settled operator decisions (2026-04-29)

24. **CL-6 cross-layer composition test (rollback + locate-suppression
    interaction).** Per Decision 5, Sprint 31.92 commits to 5 cross-layer
    composition tests (CL-1 through CL-5; above template floor + Tier 3
    sub-area D's 3-test floor). **CL-6 explicitly OUT.** Rationale per
    Decision 5: L4 (config-time startup warning) compositions with
    runtime layers (other than CL-2) are weakly meaningful in the
    operationally-relevant case; CL-2 covers the operationally-relevant
    interaction. Trade-off: exhaustive coverage vs bounded session
    count + bounded cumulative diff. Resolved in favor of bounded scope
    at Sprint 31.92. **Deferral rationale documented in
    `docs/process-evolution.md` per Decision 5 / DEF-CROSS-LAYER-EXPANSION.**
    Future cross-layer claims subject to the same protocol requirement.

25. **FAI #2 high-volume steady-state axis (`positionEndEvent` semantics
    under hundreds of variants).** Per Tier 3 item D / sub-area A
    borderline finding #B1 / DEF-FAI-2-SCOPE: S3b spike covers the
    reconnect-window axis only. High-volume steady-state behavior under
    hundreds of variants (reachable in production with hundreds of
    variants — current shadow fleet is 22) is **explicitly OUT of Sprint
    31.92 scope.** **Deferred to Sprint 31.94 reconnect-recovery work**
    where the `IBKRReconnectedEvent` producer lands and the high-volume
    steady-state semantics become naturally testable. FAI #2 scope-text
    amendment lands in Sprint 31.94. The reconnect-window axis (covered
    here) + Sprint 31.94's high-volume axis together cover both
    operationally-reachable conditions.

26. **Sprint 31.94 D3 prioritization re-evaluation.** Per Decision 6 /
    Tier 3 operator decision items #6: should Sprint 31.94 D3 (boot-time
    adoption-vs-flatten policy) be prioritized ahead of Sprint 31.93
    component-ownership? Operator decision: **NO — CONTINUE Sprint 31.92
    per Option A.** The roadmap-level question is treated as a separate
    Discovery activity per Round 2 disposition's roadmap-flag. NOT a
    Sprint 31.92 deliverable; NOT a Sprint 31.92 scope item to evaluate
    or implement. RSK-RECONSTRUCTED-POSITION-DEGRADATION's MEDIUM-HIGH
    severity (per H-R2-3) does NOT itself force the prioritization
    decision; that's a roadmap-level call. Operator daily-flatten
    mitigation continues until cessation criterion #5 satisfied.

---

## Edge Cases to Reject

The implementation should NOT handle these cases in this sprint:

1. **Two or more coroutines on the same `ManagedPosition` racing through
   the ceiling check between place-time and fill-time** — **AND, more
   broadly, between any two bookkeeping operations that mutate
   `cumulative_pending_sell_shares` or `cumulative_sold_shares` per Tier
   3 item A + B + FAI entry #9.** **REVISED per Round-1 finding C-1 +
   Tier 3 item A:** asyncio's single-threaded event loop does NOT
   serialize emit-time concurrency — coroutines yield control during
   `await place_order(...)` (and during any other `await` in callback
   paths) and a second coroutine can run the entire ceiling-check-and-place
   sequence in the gap. **The narrow race (place-time emit) IS structurally
   addressed by AC3.1's `cumulative_pending_sell_shares` reservation
   pattern via H-R2-1 atomic `_reserve_pending_or_fail` method.** **The
   broader race (callback-path bookkeeping atomicity per Tier 3 item A)
   IS structurally addressed by extending the AST-no-await scan +
   mocked-await injection regression to all 5 callback paths that mutate
   the bookkeeping counters: `on_fill` (partial-fill transfer + full-fill
   transfer), `on_cancel` (decrement), `on_reject` (decrement),
   `_on_order_status` (status-driven mutations), and the
   `_check_sell_ceiling` multi-attribute read (S4a-ii regression
   infrastructure per FAI entry #9).** Expected behavior: the second
   coroutine's `_check_sell_ceiling` returns False on the narrow race; on
   the callback-path race, the synchronous-update invariant prevents the
   torn-read (`pending` decremented but `sold` not yet incremented) that
   would cause the ceiling to artificially admit. The original Round-1
   SbC framing of this case as "asyncio prevents this" was structurally
   wrong and has been corrected; the Phase A re-entry's narrower framing
   ("only `_reserve_pending_or_fail`") was incomplete and has been
   corrected per Tier 3 item A.

2. **IBKR returning a `modifyOrder` rejection during Path #1 H2 for
   reasons other than "stop price invalid" (e.g., 201 margin rejection,
   transmit-flag conflict).** Out of scope. If S1a spike confirms H2,
   the impl assumes amend rejections are rare AND non-deterministic ones
   are caught by AC1.2's regression test (mock `IBKRBroker.modify_order`
   to raise; assert fall-through to H4 hybrid OR halt with operator
   escalation). Production-side robustness for unusual amend rejections
   is post-revenue concern; if rejection rate exceeds 5% on **worst-axis
   Wilson UB per Decision 1**, mechanism shifts to H4 hybrid per
   Hypothesis Prescription.

3. **`cumulative_pending_sell_shares` or `cumulative_sold_shares`
   integer overflow.** A `ManagedPosition` that pending-or-sold > 2³¹
   shares is architecturally infeasible (max position size is bounded
   by Risk Manager checks at single-share scale). Use `int`, not `int64`
   or `Decimal`. No overflow regression test.

4. **Operator manually placing SELL orders at IBKR outside ARGUS during
   a session.** Sprint 30 short-selling territory; reconciliation surface
   (DEC-385) catches the resulting state mismatch. AC4 ceiling applies to
   ARGUS-emitted SELLs only — manual operator actions are not in
   `_check_sell_ceiling`'s purview. Reconstructed positions specifically
   expect operator-manual flatten via `scripts/ibkr_close_all_positions.py`
   per AC3.7.

5. **Mid-session reconnect race with locate-suppression dict.** **REVISED
   per Round-1 finding H-3 + Round-2 C-R2-1 + Tier 3 item C:** if IBKR
   Gateway disconnects and reconnects mid-session, existing held orders
   are invalidated (DEF-194/195/196 cluster, Sprint 31.94). The
   locate-suppression dict in Sprint 31.92 does NOT account for reconnect
   events explicitly (no `IBKRReconnectedEvent` consumer until Sprint
   31.94 — producer doesn't exist yet). However, **AC2.5's
   broker-verification-at-timeout fallback (with new
   `Broker.refresh_positions()` ABC method per C-R2-1 + Branch 4
   `verification_stale: true` on refresh failure + HALT-ENTRY coupling
   under H1 active AND refresh failure per Tier 3 item C)** ELIMINATES the
   false-positive alert class even when stale dict entries persist
   post-reconnect. When the timeout fires: (a) `refresh_positions()` is
   called with 5s timeout; (b) on success, broker is queried for actual
   position state; (c) if expected-long observed, the alert is suppressed
   and dict entry cleared; (d) on refresh failure (Branch 4), the alert
   fires with `verification_stale: true` metadata for operator triage AND
   if H1 is the active mechanism, the position is marked
   `halt_entry_until_operator_ack=True` (no further SELL attempts; no
   phantom short). Stale dict entries during the suppression window cause
   additional SELLs at the same `ManagedPosition` to be skipped — for the
   suppression-window duration, this is conservative-but-correct.
   Reconnect-event coupling stays deferred to Sprint 31.94.

6. **Locate-rejection error string variants** ("not available for short"
   without the "contract is" prefix; "no inventory available"; non-English
   locales). S1b spike captures the exact current string `"contract is
   not available for short sale"` against ≥5 hard-to-borrow microcap
   symbols × ≥10 trials per symbol; AC2.1's substring fingerprint matches
   that exact substring (case-insensitive). Variants are caught by H5's
   "rules-out-if" condition at S1b. If S1b finds a variant, regex pattern
   is broadened at S3a. If S1b is conclusive (single string), do NOT
   speculatively broaden — fingerprint regression test fails noisy if
   string drifts. **Decision 4 strengthening:** even if a variant string
   surfaces in production paper trading and `_is_locate_rejection`
   misses it, AC2.7 watchdog (`_pending_sell_age_seconds`) auto-activates
   on first `case_a_in_production` event and provides the structural
   fallback regardless of which detection path failed.

7. **`_check_sell_ceiling` violation IN PRODUCTION-LIVE-MODE configurable
   to "warn-only" rather than "refuse SELL".** AC3.8 defaults
   `long_only_sell_ceiling_enabled = true` — fail-closed. The flag exists
   for explicit operator override during emergency rollback ONLY. There
   is NO third state ("warn-only"). Booleans only.

8. **Per-`ManagedPosition` SELL ceiling with cross-position aggregation
   across same symbol.** AC3.4 explicitly: per-`ManagedPosition`, NOT
   per-symbol. If two ManagedPositions on AAPL exist (sequential entries
   within the morning window), each has its own ceiling. Cross-position
   aggregation is the existing Risk Manager max-single-stock-exposure
   check at the entry layer (DEC-027), which is OUT of scope to modify
   here.

9. **Suppression-window expiration emits more than one alert per
   `ManagedPosition` per session.** AC2.5: when suppression expires AND
   broker-verification shows unexpected state, the next SELL emit at
   that position publishes ONE `phantom_short_retry_blocked` alert and
   clears the dict entry. Subsequent SELL emits for that position behave
   as fresh emits (no suppression, no repeat alert). Repeat alerts
   within the same session for the same position are NOT this sprint's
   problem.

10. **Path #1 mechanism (H2 amend / H4 hybrid / H1 cancel-and-await)
    handling the specific case where the bracket stop has ALREADY filled
    at the broker before the trail-stop fires.** Existing DEC-386 S1b
    path handles this via `_handle_oca_already_filled` short-circuit
    (`oca group is already filled` exception fingerprint). Sprint 31.92
    does NOT modify this path — preserve verbatim. The new mechanism
    only applies when the bracket stop is in `Submitted`/`PreSubmitted`
    state.

11. **Synthetic SimulatedBroker scenario representing a partial-fill
    pattern that doesn't occur in IBKR production.** S5a/S5b/S5c fixtures
    must reflect realistic IBKR partial-fill patterns: granularities
    matching paper IBKR observed behavior (typically full-quantity fills
    for market orders, broker-determined partials for large limit orders).
    Do NOT contrive adversarial partial-fill patterns to stress the
    ceiling — that's a different sprint's defense-in-depth.

12. **Cleanup of the 6,900 cancel-related ERROR-level lines from the Apr
    28 debrief's "Cancel-Race Noise" finding (DEF MEDIUM).** Out of
    scope — the debrief itself classifies this as LOW-priority log-volume
    hygiene. NOT a safety defect. Cleanup target: opportunistic future
    touch.

13. **The 5,348 "minimum of N orders working" IBKR rejections from the
    Apr 28 debrief.** Per the debrief: "Need circuit breaker at
    OrderManager level: if a symbol has > N pending SELLs in last M
    seconds, suppress new SELLs until reconcile completes." That circuit
    breaker IS effectively delivered by AC2 + AC3 in this sprint (AC2
    suppresses SELLs on locate-rejection symbols at position-keyed
    granularity; AC3 ceiling refuses SELLs that exceed the long quantity
    per position). A separate per-symbol pending-SELL count circuit
    breaker is NOT in scope — too speculative without measurement that
    AC2+AC3 alone are insufficient.

14. **Promotion of DEF-204 to RESOLVED status in CLAUDE.md based on
    test-suite green AND validation-artifact green ALONE.** AC5 produces
    falsifiable IN-PROCESS validation artifacts; sprint-close marks
    DEF-204 as RESOLVED-PENDING-PAPER-VALIDATION. Cessation criterion #5
    (5 paper sessions clean post-seal) is what fully closes DEF-204 in
    operational terms. The doc-sync at sprint-close must NOT use language
    that implies closure-on-merge. **AC5.1/AC5.2 framing is explicitly
    in-process logic correctness against SimulatedBroker; the JSONs are
    NOT production safety evidence.**

15. **Ceiling check at bracket placement (`place_bracket_order`).**
    **NEW per Round-1 finding H-1.** Bracket children (T1+T2+bracket-stop)
    are placed atomically against a long position; total bracket-child
    quantity equals `shares_total` by construction (AC3.2 enumerates
    ceiling check sites as 5 standalone-SELL sites only, EXCLUDING
    `place_bracket_order`); OCA enforces atomic cancellation per DEC-117
    + DEC-386 S1a. Adding ceiling check at bracket placement would block
    all bracket placements — cumulative pending+sold (0+0) + requested
    (sum of T1+T2+stop = `shares_total`) ≤ `shares_total` is technically
    true at bracket placement, but the architectural intent is that
    bracket-children placement is governed by DEC-117 atomicity, not by
    the per-emit ceiling. The ceiling exists to catch RACES across
    MULTIPLE standalone SELL emit sites, not to gate bracket-children
    placement. T1/T2/bracket-stop FILLS still increment
    `cumulative_sold_shares` per AC3.1 (because they ARE real sells; the
    position IS getting smaller).

16. **Restart-during-active-position scenarios that span multiple
    sequential entries on the same symbol.** AC3.7's `is_reconstructed
    = True` posture refuses ALL ARGUS-emitted SELLs on reconstructed
    positions. The original Round-1 reviewer's proposed `data/argus.db`
    reconstruction option (a) was explicitly REJECTED in §"Out of Scope"
    #20 because attribution of historical SELLs to specific positions
    is ambiguous when multiple sequential entries on the same symbol
    exist within a session. The conservative refusal posture handles all
    multi-position-on-symbol restart cases uniformly: ALL such positions
    are reconstructed AND ALL refuse ARGUS SELLs until Sprint 31.94 D3's
    policy decision. Operator-manual flatten via
    `scripts/ibkr_close_all_positions.py` is the only closing mechanism.
    **Edge case to reject:** asking the implementation to attempt
    finer-grained per-position restart-recovery that reads historical
    state. NOT this sprint's work.

17. **Aggregate percentage closure claims in DEC-390.** Per
    process-evolution lesson F.5 (captured at sprint-close per
    `doc-update-checklist.md` C10): DEC entries claiming closure should
    use "structural closure of mechanism X with falsifiable test fixture
    Y" rather than "closes ~Z% of blast radius." DEC-386's `~98%` claim
    was empirically falsified 24 hours later; DEC-390 must NOT repeat
    the pattern. AC6.3 mandates structural framing. **Edge case to
    reject:** any draft DEC-390 text using "comprehensive," "complete,"
    "fully closed," or "covers ~N%" language. Reviewer halts on these
    tokens.

18. **(NEW per Tier 3 item C — Branch 4 refresh-failure semantics; EXTENDED
    per Round 3 C-R3-1 — concurrent-caller serialization.)**
    Treating `Broker.refresh_positions()` failure (timeout or exception)
    as equivalent to a successful refresh with stale data, OR treating it
    as a "best-effort" warn-only path. **Branch 4 (`verification_stale:
    true`) is structurally distinct from Branches 1/2/3:** when
    `refresh_positions` raises or times out, the AC2.5 fallback does NOT
    proceed to query `broker.get_positions()` (the cache would be stale by
    definition); instead, it publishes `phantom_short_retry_blocked`
    SystemAlertEvent with metadata `{verification_stale: True,
    verification_failure_reason: type(exc).__name__, position_id, symbol}`
    AND, **if H1 is the active mechanism (per the C-R2-1↔H-R2-2 coupling
    per Tier 3 item C), additionally marks the position
    `halt_entry_until_operator_ack=True`** (no further SELL attempts; no
    phantom short; operator-driven resolution). **Edge case to reject:**
    asking the implementation to silently fall through to alert with no
    metadata (loses operator-triage signal); to retry the refresh inline
    with backoff (couples to Sprint 31.94 reconnect-recovery work); to
    skip alert emission entirely on refresh-fail (defeats the safety
    property). The structural-distinct-Branch-4 design with HALT-ENTRY
    coupling under H1 is load-bearing — this is the structural defense
    against the FAI #2 + #5 cross-falsification path.
    **Per Round 3 C-R3-1 extension:** treating concurrent
    `Broker.refresh_positions()` callers as serialized at the IBKR /
    `ib_async` layer without single-flight protection is also a rejected
    edge case. The single-flight `asyncio.Lock` + 250ms coalesce window
    per C-R3-1 Fix A is the structural defense; relying on `ib_async`'s
    internal de-duplication is NOT sufficient because the per-caller
    `wait_for(positionEndEvent)` correlation is unverified — coroutine
    A's `wait_for` may return successfully on coroutine B's
    `positionEnd`, leading to stale-for-A cache reads.

19. **(NEW per Round 3 H-R3-4 — `--allow-rollback-skip-confirm` in
    production startup.)** `--allow-rollback-skip-confirm` used in
    production startup scripts is a rejected edge case. The flag exists
    for CI ONLY; production startup MUST require the interactive ack
    per H-R3-4 fix shape — operator-presence verification at
    rollback-active boot is the structural property the flag is gating.
    Edge case to reject: operator-convenience use of the skip-confirm
    flag in production wrapper scripts to avoid the interactive prompt;
    automation that wraps `argus/main.py` with both flags set without
    explicit CI-context confirmation. Pre-live transition checklist
    flags any production startup config containing
    `--allow-rollback-skip-confirm` as a sprint-close gate (per
    `doc-update-checklist.md` C9 amendment).

20. **(NEW per Round 3 M-R3-2 — Branch 4 alert spam on repeated
    refresh-failure.)** Treating Branch 4 alert spam under repeated
    refresh-failure on the same `ManagedPosition.id` as expected
    behavior is a rejected edge case. Per M-R3-2 fix shape, Branch 4
    firings on the same `ManagedPosition.id` are throttled to one per
    hour at alert layer; first firing publishes; subsequent within
    1 hour are suppressed at alert layer (logged INFO with
    `branch_4_throttled: true`); HALT-ENTRY effect persists; throttle
    resets on `on_position_closed` or successful refresh observation.
    Edge case to reject: implementing Branch 4 as fire-on-every-trigger
    without throttle (operator-noise burden); throttling at the
    publish layer in a way that silently drops the HALT-ENTRY effect
    (the throttle is alert-layer only, not effect-layer).

21. **(NEW per Round 3 H-R3-2 — watchdog flip restart-survival.)**
    Treating the AC2.7 watchdog `auto`→`enabled` flip as surviving
    ARGUS restart is a rejected edge case. Per H-R3-2 fix shape, the
    flip is in-memory only; restart resets to `auto`. Post-restart
    `is_reconstructed=True` posture (AC3.7) provides the structural
    defense for reconstructed positions; new positions entered
    post-restart that hit case-A before the watchdog re-enables are
    exposed (RSK-WATCHDOG-AUTO-FLIP-RESTART-LOSS, MEDIUM, time-bounded
    by Sprint 31.94 D3). Edge case to reject: persisting the flipped
    state to a SQLite or in-memory cache with restart restoration —
    couples to persistence semantics that DEC-369 reconciliation
    immunity doesn't model and would re-introduce the same
    architectural sequencing problem the renumbering resolved.

---

## Scope Boundaries

### Do NOT modify

- `argus/execution/broker.py` (ABC) **EXCEPTION:** S3b adds the new
  `refresh_positions(timeout_seconds: float = 5.0) -> None` ABC method
  per C-R2-1 / Tier 3 item C. No other ABC modification permitted.
  Other ABC modifications are Sprint 31.93's prerogative.
- `argus/execution/alpaca_broker.py` — Sprint 31.95 retirement. Stub
  remains as-is.
- `argus/execution/simulated_broker.py` (semantic changes) — fixture
  subclasses in tests are acceptable (e.g.,
  `SimulatedBrokerWithRefreshTimeout` per Tier 3 item E /
  DEF-SIM-BROKER-TIMEOUT-FIXTURE lives in
  `tests/integration/conftest_refresh_timeout.py`); semantic
  modifications to production `simulated_broker.py` are OUT.
  **Exception:** S3b adds a `refresh_positions()` impl that is no-op or
  instant-success.
- `argus/execution/ibkr_broker.py::place_bracket_order` (DEC-386 S1a OCA
  threading) — preserve byte-for-byte.
- `argus/execution/ibkr_broker.py::_is_oca_already_filled_error` and
  `_OCA_ALREADY_FILLED_FINGERPRINT` — re-used by Path #1's existing
  short-circuit; NOT modified, NOT relocated.
- `argus/execution/order_manager.py::_handle_oca_already_filled`
  (DEC-386 S1b SAFE-marker path) — preserve verbatim.
- `argus/execution/order_manager.py::reconstruct_from_broker` body
  BEYOND the single-line addition `position.is_reconstructed = True`
  per AC3.7 — Sprint 31.94 D1's surface otherwise. Implementer may set
  `is_reconstructed = True` inside the function but may not modify any
  other line within the function body.
- `argus/execution/order_manager.py::reconcile_positions` Pass 1 startup
  branch + Pass 2 EOD branch (DEC-385 L3 + L5) — preserve verbatim.
- `argus/execution/order_manager.py::_check_flatten_pending_timeouts`
  3-branch side-check at lines ~3424–3489 (DEF-158 fix anchor `a11c001`)
  — preserve verbatim. Path #2's NEW upstream detection at `place_order`
  exception is added in `_flatten_position`, `_trail_flatten`,
  `_check_flatten_pending_timeouts`, `_escalation_update_stop` exception
  handlers; the EXISTING 3-branch side-check stays intact.
- `argus/main.py::check_startup_position_invariant` — Sprint 31.94 D2's
  surface.
- `argus/main.py::_startup_flatten_disabled` flag — Sprint 31.94 D2's
  surface.
- `argus/main.py:1081` (`reconstruct_from_broker()` call site) — Sprint
  31.94 D1's surface. **Exception:** S4b modifies the
  `OrderManager(...)` construction call site to pass
  `bracket_oca_type=config.ibkr.bracket_oca_type`; S4b also adds CLI
  flag parsing for `--allow-rollback` per AC4.7.
- `argus/core/health.py::HealthMonitor` consumer + `POLICY_TABLE` 13
  existing entries (DEC-388 L2) — preserve. Add ONE new `POLICY_TABLE`
  entry per AC3.9 (the 14th).
- `argus/core/health.py::rehydrate_alerts_from_db` (DEC-388 L3) —
  preserve.
- `argus/api/v1/alerts.py` REST endpoints (DEC-388 L4) — preserve.
- `argus/ws/v1/alerts.py` WebSocket endpoint (DEC-388 L4) — preserve.
- `argus/frontend/...` (entire frontend) — zero UI changes; Vitest suite
  stays at 913.
- `data/operations.db` schema (DEC-388 L3 5-table layout + migration
  framework) — preserve. New `sell_ceiling_violation` alerts use
  existing `alert_state` table; no schema migration.
- `data/argus.db` trades/positions/quality_history schemas — preserve.
  NEW: `is_reconstructed`, `cumulative_pending_sell_shares`,
  `cumulative_sold_shares`, `halt_entry_until_operator_ack` are
  in-memory `ManagedPosition` fields ONLY, NOT persisted to SQLite.
- DEC-385 / DEC-386 / DEC-388 entries in `docs/decision-log.md` —
  preserve (per Phase A leave-as-historical decision). DEC-390 is a new
  entry with cross-references; predecessors are NOT amended in-place.
- `IBKRConfig.bracket_oca_type` Pydantic validator — runtime-flippability
  preserved per DEC-386 design intent (per §"Out of Scope" #22).

### Do NOT optimize

- `argus/execution/order_manager.py` hot-path performance beyond the
  explicit benchmarks in Sprint Spec §"Performance Benchmarks".
  Correctness > speculative optimization. The file is 4,421 lines and
  structurally accommodates additional checks at scale; recalibrated
  cumulative diff bound per Tier 3: ~1150–1300 LOC.
- Test suite runtime. Adding ~88–134 effective new tests will cost
  ~30–50s of suite time; that's expected. Do NOT collapse parametrized
  tests into table-driven loops to save runtime; per-case granularity
  is load-bearing for triage when a regression fires.
- IBKR network round-trip patterns. Path #1 H1 cancel-and-await adds
  ~50–200ms per trail-stop event (fallback only); H2 amend adds ~50ms
  (preferred). AC2.5 broker-verification adds ~5.2s p95 worst-case on
  the slow path (refresh round-trip + verification call; once per
  position per session worst case). Do NOT batch or pipeline
  cancellation/amend calls — preserves DEC-117 atomic-bracket invariants.
- Locate-suppression dict GC frequency. Existing OrderManager EOD
  teardown clears the dict; suppression-timeout fallback (AC2.5 with
  Branch 4 + HALT-ENTRY coupling under H1+refresh-fail) clears entries
  on broker-verification; do NOT add a separate periodic GC sweep in
  this sprint.
- Pending-reservation increment/decrement performance. AC3.1's state
  transitions are simple integer arithmetic; do NOT add atomic operations
  or locks beyond the implicit asyncio single-threaded ordering — the
  synchronous-before-await placement (extended per Tier 3 item A to all
  bookkeeping callback paths) is the architectural correctness contract.

### Do NOT refactor

- `argus/execution/order_manager.py` module structure (4,421 lines,
  multiple class methods, mixed concerns). Tempting to break into
  smaller files; that's Sprint 31.93 component-ownership work. Preserve
  current structure verbatim.
- `argus/core/config.py::OrderManagerConfig` Pydantic model class
  structure beyond ADDING the 4 new fields (3 Round-1-revised + 1 NEW
  per Decision 4 — `pending_sell_age_watchdog_enabled`). Field ordering,
  validator decorators, docstring style — leave as-is.
- `argus/core/config.py::IBKRConfig::bracket_oca_type` — already exists;
  AC4 only changes the CONSUMER side (OrderManager). The Pydantic field
  declaration is preserved (per §"Out of Scope" #22 — validator
  restriction to literal `1` is REJECTED — DEC-386 rollback escape
  hatch preserved with AC4.6 + AC4.7 mitigation).
- `tests/execution/order_manager/` directory layout. New test files
  follow existing naming convention (`test_def204_round2_path{1,2}.py`,
  `test_def204_round2_ceiling.py`, `test_def204_callback_atomicity.py`,
  `test_def212_oca_type_wiring.py`); do NOT consolidate into mega-modules.
- DEF-158 retry 3-branch side-check (lines ~3424–3489). Tempting to add
  a 4th branch for locate-rejection; explicitly REJECTED at Phase A.
  The locate-rejection detection is upstream (at `place_order` exception
  in the 4 SELL emit sites), not in the side-check.
- `ManagedPosition` class structure beyond ADDING the 4 new fields
  (`is_reconstructed`, `cumulative_pending_sell_shares`,
  `cumulative_sold_shares`, `halt_entry_until_operator_ack`). Field
  ordering, dataclass decorators, default-value patterns — leave as-is.

### Do NOT add

- New alert types beyond `sell_ceiling_violation`. The Apr 28 debrief
  and the protocol allow it implicitly, but Sprint 31.91 already added
  `phantom_short`, `phantom_short_retry_blocked`, `eod_residual_shorts`,
  `eod_flatten_failed`, `cancel_propagation_timeout`, `ibkr_disconnect`,
  `ibkr_auth_failure`, plus heartbeat — the alert taxonomy is healthy.
  Branch 4 reuses `phantom_short_retry_blocked` with new
  `verification_stale: true` metadata; no new alert type.
- New REST endpoints for ceiling-violation history queries. Existing
  `/api/v1/alerts/history` filtered by `alert_type=sell_ceiling_violation`
  covers it.
- New Pydantic config models. The 4 new fields land on EXISTING
  `OrderManagerConfig` (3 from Round-1-revised + 1 NEW per Decision 4 —
  `pending_sell_age_watchdog_enabled`). The 1 existing
  `IBKRConfig.bracket_oca_type` field gains a new consumer (OrderManager)
  but no schema change.
- New SQLite tables. `sell_ceiling_violation` alerts persist via DEC-388
  L3 `alert_state` table.
- New CLI tools beyond the 4 spike/validation scripts. **Exception:**
  `--allow-rollback` flag added to existing `argus/main.py` per AC4.7;
  no new CLI tool, just a new flag on existing entry point.
- New helper modules under `argus/execution/`. The 2 new helpers
  (`_is_locate_rejection` in `ibkr_broker.py`, `_check_sell_ceiling` and
  `_reserve_pending_or_fail` in `order_manager.py`) live in their
  respective existing modules.
- A `sell_ceiling_violations` table separate from `alert_state`. Re-use
  existing infrastructure.
- A `/api/v1/orders/sell_volume_ceiling_status` endpoint for monitoring.
  Out of scope. The alert path is the operator interface.
- A separate `_handle_locate_suppression_timeout` helper in a new module.
  The broker-verification logic per AC2.5 (with Branch 4 + HALT-ENTRY
  coupling) lives inline in `_check_flatten_pending_timeouts` housekeeping
  loop OR as a private method on OrderManager.

---

## Interaction Boundaries

### This sprint does NOT change the behavior of:

- `Broker.cancel_all_orders()` ABC contract. DEC-386 S0's signature
  `cancel_all_orders(symbol: str | None = None, *, await_propagation:
  bool = False)` is consumed unchanged in H1 fallback path. AC1 calls
  it with `(symbol=position.symbol, await_propagation=True)` — same call
  shape DEC-386 S1c uses.
- `IBKRBroker.place_bracket_order()` external contract. Bracket OCA
  threading semantics, atomic placement, error 201 handling — all
  preserved.
- `IBKRBroker.place_order()` external contract. The `place_order(Order)`
  API is unchanged. Path #2's NEW behavior is at the CALLER side: callers
  wrap `place_order(SELL)` calls with `_check_sell_ceiling` pre-check
  (via `_reserve_pending_or_fail` per H-R2-1) + `_is_locate_suppressed`
  pre-check + `_is_locate_rejection` post-classification, but the broker
  method itself is unchanged.
- `IBKRBroker.modify_order()` external contract. Existing interface;
  AC1's H2 path calls it with `(stop_order_id, new_aux_price=current_price)`.
  NO new keyword arguments, NO new return-value semantics.
- `OrderManager.on_fill()` event handler external contract. Internal:
  AC3.1 enumerates `cumulative_pending_sell_shares` decrement +
  `cumulative_sold_shares` increment for SELL fills.
  Synchronous-update invariant per Tier 3 items A + B applies. Existing
  T1/T2/bracket-stop fill processing preserved.
- `Position` / `ManagedPosition` data model external contract. AC3.1 +
  AC3.7 + Tier 3 item C add FOUR new fields (`cumulative_pending_sell_shares:
  int = 0`, `cumulative_sold_shares: int = 0`, `is_reconstructed: bool =
  False`, `halt_entry_until_operator_ack: bool = False`) with default
  values; existing serialization and DB columns preserved. New fields
  are in-memory only — NOT persisted to SQLite (per Sprint 35+ DEF-209
  backlog deferral; conservative `is_reconstructed` posture handles
  restart-safety per AC3.7).
- `SystemAlertEvent` schema. DEC-385 L2 added `metadata: dict[str, Any] |
  None`; preserved. New `sell_ceiling_violation` alert uses existing
  schema. Branch 4's `verification_stale: true` metadata uses the
  existing field.
- `OrderManagerConfig` external contract. Adding 4 new fields with
  defaults is backward-compatible; existing YAML configs without these
  fields default safely.
- `IBKRConfig` external contract. AC4.1 only changes the CONSUMER side;
  the field definition is unchanged. Per §"Out of Scope" #22, validator
  restriction to literal `1` is REJECTED.
- `HealthMonitor.consume_alert()` consumer logic. AC3.9 adds ONE
  `POLICY_TABLE` entry; the consumer logic is preserved.
- WebSocket `/ws/v1/alerts` event payload schema (4 lifecycle deltas).
  New `sell_ceiling_violation` alert flows through `alert_active` delta
  unchanged. Branch 4's `verification_stale: true` metadata flows
  through existing schema.
- REST `/api/v1/alerts/active`, `/history`, `/{id}/acknowledge`,
  `/{id}/audit`. Behavior unchanged.

### This sprint does NOT affect:

- Any frontend component. Zero `.tsx`, `.ts`, `.css`, or test file in
  `frontend/` is touched.
- Any catalyst pipeline component (CatalystPipeline, CatalystClassifier,
  BriefingGenerator, CatalystStorage). Zero changes.
- Any quality engine component (SetupQualityEngine, DynamicPositionSizer,
  QualitySignalEvent flow). Zero changes.
- Any data service component (DatabentoDataService, IntradayCandleStore,
  FMP/Finnhub clients, UniverseManager). Zero changes.
- Any backtesting component (BacktestEngine, VectorBT path, replay
  harness, PatternBacktester). Zero changes.
- Any AI Layer component (ClaudeClient, PromptManager, ActionManager,
  ConversationManager). Zero changes.
- Strategy modules (any file in `argus/strategies/`). Zero changes —
  entry-side logic is unaffected by exit-side mechanism changes.
- Pattern modules (any file in `argus/strategies/patterns/`). Zero
  changes.
- Risk Manager (`argus/core/risk_manager.py`). Zero changes — DEC-027
  approve-with-modification posture preserved.
- Orchestrator (`argus/core/orchestrator.py`). Zero changes.
- `data/argus.db` trades/positions/quality_history schemas. Zero
  migrations.
- `data/counterfactual.db`, `data/experiments.db`, `data/learning.db`,
  `data/catalyst.db`, `data/vix_landscape.db`, `data/regime_history.db`,
  `data/evaluation.db`. Zero schema changes.

---

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| `_is_oca_already_filled_error` relocation from `ibkr_broker.py` to `broker.py` (Tier 3 #1 Concern A) | Sprint 31.93 | (Tier 3 #1 verdict, Concern A) |
| Component-ownership refactor of OrderManager construction site in `argus/main.py` lifespan | Sprint 31.93 | DEF-175, DEF-182, DEF-201, DEF-202 |
| `ReconstructContext` parameter on `reconstruct_from_broker()` (D1) | Sprint 31.94 | DEF-211 D1 |
| IMPROMPTU-04 startup invariant gate refactor (D2) | Sprint 31.94 | DEF-211 D2 |
| Boot-time adoption-vs-flatten policy decision for broker-only LONG positions (D3) — **eliminates RSK-RECONSTRUCTED-POSITION-DEGRADATION** | Sprint 31.94 | DEF-211 D3 |
| `IBKRReconnectedEvent` producer + consumer wiring (gates DEF-222 audit; couples to locate-suppression dict-clear) | Sprint 31.94 | DEF-194, DEF-195, DEF-196, DEF-222 |
| **FAI #2 high-volume steady-state axis (`positionEndEvent` semantics under hundreds of variants)** | **Sprint 31.94** | **DEF-FAI-2-SCOPE (NEW per Tier 3 item D)** |
| **CL-6 cross-layer composition test (rollback + locate-suppression interaction)** | **Unscheduled (deferral rationale documented per Decision 5)** | **DEF-CROSS-LAYER-EXPANSION (NEW per Tier 3 sub-area D)** |
| RejectionStage enum split (`MARGIN_CIRCUIT` + `TrackingReason`) | Sprint 31.94 | DEF-177, DEF-184 |
| DEF-014 IBKR emitter TODOs | Sprint 31.94 | DEF-014 (closed in 31.91 but emitter TODO remnants) |
| Alpaca incubator retirement | Sprint 31.95 | DEF-178, DEF-183 |
| `evaluation.db` 22GB legacy file VACUUM (operator-side, post-Sprint-31.915 retention) | Operator action, immediate | (operational task, not DEF) |
| Reconciliation-WARNING per-cycle throttling | Deferred (revisit if observed ≥10 cycles post-Sprint-31.92-seal-+-5-paper-sessions) | DEF-215 |
| 4,700 broker-overflow routings analysis (`max_concurrent_positions: 50` sizing review) | Unscheduled (separate analysis pass) | (filed at Apr 28 debrief Action Items §4 — no DEF) |
| 6,900 cancel-related ERROR-line log-volume cleanup | Opportunistic / unscheduled | (Apr 28 debrief Findings §LOW) |
| Per-symbol pending-SELL count circuit breaker (separate from AC2 + AC3) | Unscheduled (revisit if AC2+AC3 prove insufficient post-merge) | (Apr 28 debrief Findings §MEDIUM) |
| `ibkr_close_all_positions.py` post-run verification feature | Unscheduled — operator-tooling, not a defect | (no DEF; retracted at Phase A 2026-04-29) |
| Live-trading test fixture (`tests/integration/test_live_config_stress.py`) | Sprint 31.93 OR Sprint 31.94 | DEF-208 |
| `ManagedPosition.redundant_exit_observed` SQLite persistence | Sprint 35+ Learning Loop V2 | DEF-209 (folded by DEC-386 Tier 3 #1) |
| `ManagedPosition.cumulative_pending_sell_shares` + `cumulative_sold_shares` + `is_reconstructed` + `halt_entry_until_operator_ack` SQLite persistence | Sprint 35+ Learning Loop V2 (DEF-209 extended scope) | DEF-209 |
| Standalone `sell_volume_ceiling_status` REST endpoint | Unscheduled (out of scope here) | (no DEF) |
| Locate-suppression dict reconnect-event awareness (couples with `IBKRReconnectedEvent` consumer) | Sprint 31.94 | (filed at S3a as deferred sub-item, no DEF; mitigated by AC2.5 broker-verification + Branch 4 + HALT-ENTRY coupling per Tier 3 item C) |
| Locate-rejection error-string drift quarterly re-validation | Operational hygiene, post-Sprint-31.92-merge | RSK-DEC-390-FINGERPRINT (proposed at sprint-close) |
| Path #1 H2 amend-stop-price IBKR-API-version assumption documentation | `docs/live-operations.md` paragraph at sprint-close | RSK-DEC-390-AMEND (proposed at sprint-close) |
| Path #1 H1 cancel-and-await unprotected-window documentation | `docs/live-operations.md` paragraph at sprint-close (only if H1 selected) | RSK-DEC-390-CANCEL-AWAIT-LATENCY (proposed at sprint-close, conditional on H1 selection) |
| **Sprint 31.94 D3 prioritization re-evaluation (Decision 6 — separate Discovery activity)** | **Discovery (separate activity, NOT a sprint deliverable)** | **(roadmap-level question per Decision 6)** |

---

## Adversarial Round 3 Reference (full scope per Outcome C)

The Adversarial Review Input Package Round 3 (Phase C, artifact #9
revised) embeds this Spec by Contradiction verbatim. **Round 3 scope is
FULL, not narrowed** — the 2026-04-29 amendment supersedes Round 2
disposition's narrowest-scope recommendation. Round 3 reviewers should
specifically scrutinize:

1. Whether the C-1 fix (pending reservation pattern) introduces NEW races
   at state-transition boundaries — specifically, whether the
   synchronous-update invariant per Tier 3 items A + B (FAI entry #9)
   correctly extends to `on_fill` partial-fill transfer, `on_cancel`
   decrement, `on_reject` decrement, `_on_order_status` mutations, AND
   the `_check_sell_ceiling` multi-attribute read.
2. Whether the C-2 fix (`is_reconstructed` refusal posture) creates
   legitimate-flatten-blocked failure modes that the operator
   daily-flatten script doesn't catch — specifically, EOD scenarios on
   reconstructed positions. **Note (per H-R2-3):** RSK-RECONSTRUCTED-POSITION-DEGRADATION
   re-rated to MEDIUM-HIGH per Severity Calibration Rubric; Sprint Abort
   Condition #7 trigger lowered from 4 weeks to 2 weeks; Sprint 31.94 D3
   prioritization remains a separate Discovery activity per Decision 6.
3. Whether the C-R2-1 fix (Branch 4 refresh-failure semantics + HALT-ENTRY
   coupling under H1 active AND refresh failure per Tier 3 item C)
   correctly closes the FAI #2 + #5 cross-falsification path —
   specifically, whether CL-3 cross-layer test using
   `SimulatedBrokerWithRefreshTimeout` fixture (DEF-SIM-BROKER-TIMEOUT-FIXTURE)
   actually exercises the composite failure mode, OR whether the fixture's
   in-process simulation diverges from production refresh-timeout behavior.
4. Whether the H-R2-4 combined fix (AC4.6 dual-channel CRITICAL warning +
   AC4.7 `--allow-rollback` CLI gate) is operationally meaningful — could
   the warning be missed in log noise even with dual-channel emission?
5. Whether the M-R2-1 fix (Decision 4 watchdog auto-activation) genuinely
   closes the FAI #4 measured-only acceptance — specifically, whether the
   `auto`/`enabled`/`disabled` config field's auto-flip semantics at
   first `case_a_in_production` event are correctly atomic.
6. Whether the M-R2-3 fix (Pytest with JSON side-effect for composite
   validation) genuinely preserves freshness — what if the daily CI
   workflow is misconfigured or fails silently?
7. Whether items 20–26 in §"Out of Scope" (specifically rejecting
   reviewer-proposed alternatives + rejecting CL-6 + rejecting FAI #2
   high-volume + rejecting Sprint 31.94 D3 prioritization) are correctly
   justified or whether one of them should be reopened.
8. Whether new Edge Case to Reject #1 (race scenario via reservation
   pattern + broader synchronous-update invariant per Tier 3 item A) is
   structurally airtight. **FAI cross-check is mandatory and explicit per
   Outcome C protocol.**
9. Whether new Edge Case to Reject #15 (ceiling check at bracket placement
   excluded) is correctly bounded — i.e., what about non-standard
   bracket-children placements that might exist in DEC-386 broker-only
   paths?
10. Whether new Edge Case to Reject #16 (multi-position-on-symbol restart
    scenarios) creates an operationally undesirable "trapped capital"
    failure mode — and whether Sprint 31.94 D3's policy decision adequately
    resolves it.
11. Whether new Edge Case to Reject #17 (no aggregate percentage claims) is
    structurally enforceable or whether it relies on implementer discipline
    alone.
12. Whether new Edge Case to Reject #18 (Branch 4 refresh-failure semantics
    per Tier 3 item C) is structurally distinct enough from Branches 1/2/3
    to prevent silent fall-through.
13. Whether the deferred items table (especially the locate-suppression
    dict reconnect-event coupling + FAI #2 high-volume axis +
    Sprint 31.94 D3 prioritization) accumulates too much technical debt at
    the Sprint 31.94 boundary.
14. **FAI cross-check (mandatory per `protocols/adversarial-review.md`
    v1.1.0 § Outcome C):** Identify any primitive-semantics assumption
    load-bearing on the proposed mechanism that is NOT in the FAI's 9
    entries. Per the inventory's self-falsifiability clause, any new
    finding indicates the inventory has failed. **Phase A Tier 3 already
    exercised this clause once (entry #9 added 2026-04-29). Round 3 is
    the next layer.** Decision 7 (operator pre-commitment) routes the
    response: primitive-semantics-class Critical → Phase A re-entry; any
    other Critical class → RSK-and-ship.

---

# Embedded: Sprint-Level Regression Checklist

> Source: `regression-checklist.md` (Phase C re-sealed, 2026-04-29; 34 invariants).

# Sprint 31.92: Sprint-Level Regression Checklist

> **Phase C artifact 6/9 (revised post-Round-2-Disposition + Phase A
> Re-entry + Phase A Tier 3 + Phase B re-run).** Specific, testable items
> the `@reviewer` must verify at every Tier 2 review. Embedded into every
> implementation prompt so the implementer can self-check before close-out
> and the reviewer has explicit assertions to test against.
>
> **Revision history:** Round 1 authored 2026-04-28 with 18 invariants.
> Round-1-revised 2026-04-29: invariant 13 rewritten for pending-reservation
> pattern (C-1); invariant 14 expanded for position-keyed dict +
> broker-verification (H-2 + H-3); invariant 16 reframed as
> lock-step-not-validity (H-4); invariant 17 reframed for
> mechanism-conditional AMD-2 (C-3); NEW invariant 19 (`is_reconstructed`
> refusal); NEW invariant 20 (pending-reservation state-transition
> completeness); NEW invariant 21 (broker-verification three-branch
> coverage); NEW invariant 22 (mechanism-conditional operator-audit
> logging). Round 2 carried over to 22 invariants (no net invariant change;
> 14 dispositions distributed across existing invariants). **This Phase C
> revision (2026-04-29) adds invariants 23–27 per Phase B design summary
> § Regression Invariants and Tier 3 verdict items A–E + Decisions 3–5.**
> Total invariants: **27**.

## Critical Invariants (Must Hold After Every Session)

The 27 invariants are organized into four groups:
- **Invariants 1–9: PRESERVED FROM PRIOR SPRINTS** — DEC-117/364/369/372/385/386/388 + DEF-158 + `# OCA-EXEMPT:`.
- **Invariants 10–12: BASELINE PRESERVATION** — test count, pre-existing flake count, frontend immutability.
- **Invariants 13–22: NEW IN SPRINT 31.92 ROUND-1-REVISED** — established by AC1/AC2/AC3/AC4 (with Round-1 revisions, preserved through Round 2 and Phase A re-entry).
- **Invariants 23–27: NEW PER PHASE B RE-RUN (Tier 3 items A–E + Decisions 3–5)** — synchronous-update invariant scope extension, HALT-ENTRY coupling, Branch 4, AC2.7 auto-activation, 5 cross-layer compositions.

### 1. DEC-117 Atomic Bracket Order Placement

**Test:** `tests/execution/test_atomic_brackets.py` (existing) — parent + 2 children placed atomically; parent failure cancels children; transmit-flag semantics preserved.

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b (Path #1 mechanism touches `_trail_flatten` + `_resubmit_stop_with_retry`'s emergency-flatten branch, both of which interact with bracket-stop cancellation OR amendment timing — must not regress atomic bracket invariants); S5c CL-2 explicitly stresses bracket invariants under `bracket_oca_type != 1` rollback.

**Sessions responsible:** ALL.

---

### 2. DEC-364 `cancel_all_orders()` No-Args ABC Contract

**Test:** Pre-existing regression test that asserts `Broker.cancel_all_orders()` (no args) preserves DEC-364 behavior; DEC-386 S0's positional+keyword signature is BACKWARD-COMPATIBLE (zero-arg call = original DEC-364 behavior).

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b (if Path #1 mechanism uses H1 cancel-and-await fallback, calls go through this ABC; must preserve no-args semantics for any existing callers).

**Sessions responsible:** ALL.

---

### 3. DEC-369 Broker-Confirmed Reconciliation Immunity

**Test:** Pre-existing test that broker-confirmed positions (with IBKR entry fill callbacks, `oca_group_id is None`-derived from `reconstruct_from_broker`) are NOT auto-closed by reconciliation. AC3.6 + AC3.7 must compose with this: ceiling initialization for reconstruct-derived positions composes additively with DEC-369 immunity (BOTH protections apply; `is_reconstructed = True` adds a second layer of refusal, not a replacement).

**Verified at:** Every session's close-out. **Critical for:** S4a-i (ceiling initialization for `reconstruct_from_broker`-derived positions per AC3.6 + AC3.7); S5b restart-during-active-position validation.

**Sessions responsible:** ALL.

---

### 4. DEC-372 Stop Retry Caps + Exponential Backoff

**Test:** Pre-existing `test_stop_resubmission_cap` — retry attempts capped per config; backoff is 1s → 2s → 4s; emergency-flatten fires only after cap exhausted.

**Verified at:** Every session's close-out. **Critical for:** S2b (touches the emergency-flatten branch in `_resubmit_stop_with_retry`; must preserve retry-cap and backoff invariants while applying Path #1 mechanism to the emergency SELL).

**Sessions responsible:** ALL; especially S2b.

---

### 5. DEC-385 Six-Layer Side-Aware Reconciliation

**Test:** Pre-existing monotonic-safety matrix regression `test_def204_reconciliation_layers_monotonic` (Sprint 31.91 invariant 17). All 6 layers preserved byte-for-byte.

**Verified at:** Every session's close-out. **Critical for:** S3a + S3b (Path #2's broker-verified suppression-timeout fallback REUSES `phantom_short_retry_blocked` alert from DEC-385 L4 conditional on broker-verification result; must not modify the alert path itself); S5c CL-3 + Branch 4 unit test (uses the alert path under `verification_stale: true` metadata).

**Sessions responsible:** ALL; especially S3a, S3b, S5c.

**Specific edges:**
- DEF-158 retry 3-branch side-check (lines ~3424–3489) UNCHANGED — Path #2 adds upstream detection at `place_order` exception, NOT a 4th branch.
- `phantom_short_retry_blocked` SystemAlertEvent emitter unchanged in source code — Path #2's broker-verified fallback CALLS this existing emitter conditionally per AC2.5 case (c) + Branch 4.

---

### 6. DEC-386 Four-Layer OCA Architecture

**Test:** Pre-existing monotonic-safety matrix regression `test_dec386_oca_layers_preserved`. All 4 layers preserved byte-for-byte.

**Verified at:** Every session's close-out. **Critical for:** S4b (DEF-212 rider modifies `OrderManager.__init__` and the 4 OCA-thread sites; the OCA-threading SEMANTICS must remain identical — only the source of `ocaType` value changes from module constant to instance attribute).

**Sessions responsible:** ALL; especially S4b.

**Specific edges:**
- `IBKRBroker.place_bracket_order` OCA threading (DEC-386 S1a) UNCHANGED.
- `_handle_oca_already_filled` SAFE-marker path (DEC-386 S1b) UNCHANGED.
- `# OCA-EXEMPT:` exemption mechanism preserved (see invariant 9).
- `_is_oca_already_filled_error` helper UNCHANGED (relocation deferred to Sprint 31.93 per SbC §"Out of Scope" #4).
- `bracket_oca_type` Pydantic field validator UNCHANGED — runtime-flippability preserved per DEC-386 design intent (rollback escape hatch). Only the consumer side (OrderManager) gains construction-time wiring + AC4.6 dual-channel startup warning + AC4.7 `--allow-rollback` CLI gate.

---

### 7. DEC-388 Alert Observability Subsystem

**Test:** Pre-existing tests for HealthMonitor consumer + REST + WebSocket + 5-layer storage. AST policy-table exhaustiveness regression `tests/api/test_policy_table_exhaustiveness.py` updated at S4a-i to include `sell_ceiling_violation` (now 14 entries).

**Verified at:** Every session's close-out. **Critical for:** S4a-i (adds 1 new alert type `sell_ceiling_violation` and 1 new `POLICY_TABLE` entry; must preserve all 13 existing entries) and S3b (Path #2's broker-verified fallback emits `phantom_short_retry_blocked` via the existing DEC-385 path conditionally — no new emitter site at the consumer side; Branch 4 publishes the same alert with `verification_stale: true` metadata).

**Sessions responsible:** ALL; especially S4a-i, S3b.

**Specific edges:**
- `POLICY_TABLE` count: 13 (pre-S4a-i) → 14 (post-S4a-i).
- `sell_ceiling_violation` policy entry: `operator_ack_required=True`, `auto_resolution_predicate=None` (manual-ack only).
- Existing 13 policy entries unchanged.
- Branch 4 alert metadata extends but does NOT replace the existing `phantom_short_retry_blocked` policy entry.

---

### 8. DEF-158 Retry Three-Branch Side-Check Preserved Verbatim

**Test:** New regression test `test_def158_3branch_side_check_preserved_verbatim` (S3b). Asserts that `_check_flatten_pending_timeouts` lines ~3424–3489 retain the BUY → resubmit / SELL → alert+halt / unknown → halt structure UNCHANGED. Path #2's NEW detection is at the `place_order` exception in the 4 SELL emit sites, NOT inside this gate.

**Verified at:** S3b close-out specifically; reviewed at every session as a do-not-modify boundary.

**Sessions responsible:** ALL; especially S3b. **A-class halt A5** fires if violated.

---

### 9. `# OCA-EXEMPT:` Exemption Mechanism Preserved

**Test:** Pre-existing grep regression guard `test_no_sell_without_oca_when_managed_position_has_oca` from DEC-386 S1b.

**Verified at:** Every session's close-out. **Critical for:** S2a, S2b, S3b, S4a-i (any new SELL emit logic must either use OCA threading via `position.oca_group_id` OR carry an `# OCA-EXEMPT: <reason>` comment).

**Sessions responsible:** ALL.

---

### 10. Test Count Baseline Holds

**Test:** Full suite pytest count ≥ 5,269 at every close-out. Vitest count = 913 unchanged.

**Verified at:** Every session's close-out. **B-class halt B3** fires if pytest drops below baseline.

**Sessions responsible:** ALL.

**Per-session test deltas (revised per Phase B re-run):**

| Session | Pytest Δ | Vitest Δ |
|---------|---------:|---------:|
| S1a | 0 | 0 |
| S1b | 0 | 0 |
| S2a | +6 to +7 | 0 |
| S2b | +7 | 0 |
| S3a | +6 | 0 |
| S3b | +9 | 0 |
| S4a-i | +7 logical (≈9 effective) | 0 |
| S4a-ii | **+7 NEW** | 0 |
| S4b | +7 logical (≈11 effective with parametrize) | 0 |
| S5a | +4 | 0 |
| S5b | +9 logical | 0 |
| S5c | **+6 NEW** (5 CL tests + 1 Branch 4 unit test) | 0 |
| **Total range** | **+88 to +114** | **0** |

**Final target:** 5,357–5,403 pytest + 913 Vitest at S5c close-out.

---

### 11. Pre-Existing Flake Count Does Not Increase

**Test:** Run full suite at every session close-out; count failures attributable to DEF-150, DEF-167, DEF-171, DEF-190, DEF-192. Flake count ≤ baseline.

**Verified at:** Every session's close-out. **B-class halt B1** fires if any flake worsens or new flake appears.

**Sessions responsible:** ALL.

---

### 12. Frontend Immutability

**Test:** `git diff <session-base>..HEAD -- 'frontend/'` returns empty for every session. Vitest count = 913 at every close-out.

**Verified at:** Every session's close-out. **B-class halt B8** fires if violated.

**Sessions responsible:** ALL.

---

### 13. Long-Only SELL-Volume Ceiling: `cumulative_pending_sell_shares + cumulative_sold_shares + requested_qty ≤ shares_total` Per `ManagedPosition`

**Test:** New parametrized test `test_check_sell_ceiling_blocks_excess_sell_at_5_emit_sites_parametrized` (S4a-i, parametrized × 2 emit sites + S5b composite × remaining 3 emit sites + reconstructed-position refusal scenarios).

**REWRITTEN per Round-1 C-1; SCOPE EXTENDED per Tier 3 item A + B + entry #9:** Ceiling is a TWO-COUNTER reservation: `cumulative_pending_sell_shares` (incremented synchronously at place-time before `await`) + `cumulative_sold_shares` (incremented at fill). Ceiling check: `pending + sold + requested ≤ shares_total`. The race scenario (two coroutines on same `ManagedPosition`) is structurally prevented because the second coroutine's check sees the first coroutine's pending reservation. **The synchronous-update invariant extends to ALL bookkeeping mutation paths per Tier 3 entry #9 (see invariant 23 below for the AST regression infrastructure).**

**Verified at:** S4a-i close-out (2 of 5 sites parametrized + C-1 race test); S5b close-out (remaining 3 sites + composite stress test + reconstructed-position refusal); S5c CL-1 (force false-positive in `_reserve_pending_or_fail`, ceiling catches at reconciliation). **A-class halt A11** fires if false-positives observed in production paper trading.

**Sessions responsible:** S4a-i, S4a-ii (callback-path scope extension), S5b, S5c.

**Specific edges:**
- Per-`ManagedPosition`, NOT per-symbol (AC3.4).
- `reconstruct_from_broker`-derived: initialize `cumulative_pending_sell_shares = 0`, `cumulative_sold_shares = 0`, `is_reconstructed = True`, `shares_total = abs(broker_position.shares)` (AC3.6).
- Reconstructed positions refuse ALL ARGUS-emitted SELLs regardless of pending+sold+requested arithmetic (AC3.7) — early return in ceiling check before counter math.
- Config-gated: `OrderManagerConfig.long_only_sell_ceiling_enabled = false` returns True unconditionally (AC3.8).
- Increment in `on_fill` for SELL-side fills only — T1, T2, bracket stop, trail-flatten, escalation-flatten, retry-flatten, EOD-flatten, locate-released-flatten (AC3.1).
- Bracket placement EXCLUDED from ceiling check (AC3.2 + SbC §"Edge Cases to Reject" #15).
- **Stop-replacement ceiling exemption** (H-R2-5): `_check_sell_ceiling` accepts `is_stop_replacement: bool=False`; exemption permitted ONLY at `_resubmit_stop_with_retry` normal-retry path. AST callsite scan regression invariant 24 (existing) extended with reflective-pattern coverage per invariant 23.

---

### 14. Path #2 Locate-Rejection Fingerprint Deterministic + Position-Keyed Suppression + Broker-Verified Timeout

**Test:** Composite of multiple sub-tests (S3a + S3b):
1. `test_is_locate_rejection_matches_canonical_string` — exact substring captured by S1b spike, case-insensitive.
2. `test_is_locate_suppressed_position_keyed_returns_true_within_window` — keyed by `ManagedPosition.id` (ULID), NOT symbol (Round-1 H-2).
3. `test_suppression_timeout_broker_shows_*` × 3 branches — AC2.5 broker-verification three-branch coverage (Round-1 H-3).
4. **NEW per Tier 3 item C:** Branch 4 + HALT-ENTRY coupling tests (see invariants 24 + 25 below for the regression infrastructure).

**EXPANDED per Round-1 H-2 + H-3 + Tier 3 item C.**

**Verified at:** S3a close-out (sub-tests 1+2); S3b close-out (sub-test 3 broker-verification + Branch 4 + HALT-ENTRY coupling); ongoing at quarterly re-validation (RSK-DEC-390-FINGERPRINT — operational hygiene). **A-class halts A2 + A13 + B12** apply.

**Sessions responsible:** S3a (establishes); S3b (broker-verification wiring + Branch 4 + HALT-ENTRY coupling); S5b (validates against synthetic locate-rejection fixture with hold-then-release); S5c (CL-3 cross-layer composition).

**Specific edges:**
- Substring match (NOT regex unless S1b finds variants) — case-insensitive via `str(error).lower()`.
- Helper accepts `BaseException` (mirrors DEC-386's `_is_oca_already_filled_error` shape).
- Suppression dict keyed by `ManagedPosition.id` (ULID) — cross-position safety preserved.
- Broker-verification at AC2.5 timeout: 3 outcomes (broker-zero, broker-expected-long, broker-unexpected-state) + Branch 4 (`verification_stale: true`) on refresh failure.
- `Broker.refresh_positions(timeout_seconds=5.0)` is the new ABC method introduced at S3b (per C-R2-1).

---

### 15. `_OCA_TYPE_BRACKET` Module Constant Deleted

**Test:** New grep regression guard `test_no_oca_type_bracket_constant_remains_in_module` (S4b). Greps `argus/execution/order_manager.py` for the literal `_OCA_TYPE_BRACKET` and asserts ZERO matches post-S4b.

**Verified at:** S4b close-out; every subsequent session as a non-regression check. **B-class halt B11** fires if the count is wrong before S4b begins.

**Sessions responsible:** S4b (establishes); S5a, S5b, S5c (preserve).

**Specific edges:**
- Pre-S4b: 5 occurrences (1 declaration + 4 use sites).
- Post-S4b: 0 occurrences. All replaced by `self._bracket_oca_type`.
- `OrderManager.__init__` accepts `bracket_oca_type: int` keyword arg; `argus/main.py` construction site passes `config.ibkr.bracket_oca_type`.
- Absolute line numbers in spec text are DIRECTIONAL ONLY per protocol v1.2.0+; structural anchors (the constant name + the function/class names containing the use sites) bind.

---

### 16. AC4.4 OCA-Type Lock-Step (NOT Operational Validity) — `bracket_oca_type=0` Threads Through Consistently

**Test:** New parametrized test `test_bracket_oca_type_lockstep_preserved_under_rollback` (S4b, parametrized × 4 OCA-thread sites with `bracket_oca_type ∈ {0, 1}`). Asserts that flipping from 1 to 0 produces consistent `ocaType=0` on bracket children AND on standalone-SELL OCA threading (NO divergence).

**REFRAMED per Round-1 H-4:** Test affirms the lock-step PROPERTY of the DEF-212 fix; does NOT affirm `ocaType=0` as operationally valid. Test docstring explicitly: "ocaType=0 disables OCA enforcement and reopens DEF-204; this test asserts the rollback path is consistent, not that the rollback is operationally safe."

**Verified at:** S4b close-out. S5c CL-2 stresses lock-step under rollback as a cross-layer composition (verifies emergency-flatten branch still ceiling-checks even when L4 is in rollback mode).

**Sessions responsible:** S4b (establishes); S5c (cross-layer composition).

---

### 17. AMD-2 Invariant Mechanism-Conditional (H2 Preserved / H4 Mixed / H1 Superseded)

**Test:** S2a updates the existing AMD-2 regression test (`test_amd2_sell_before_cancel` — Sprint 28.5 era) per S1a-selected mechanism:
- **If H2 (default):** Existing test PRESERVED unchanged. New test `test_path1_h2_amend_called_before_any_sell_emit` asserts `modify_order` ordering. AMD-2 invariant intact.
- **If H4 (hybrid):** Parametrized over success and fallback branches; AMD-2 preserved on amend-success path; AMD-2-prime asserted on cancel-fallback path.
- **If H1 (last-resort):** Existing test renamed `test_amd2_modified_cancel_and_await_before_sell`; asserts new ordering. DEC-390 must explicitly call out H1 as last-resort with rationale. AC1.6 operator-audit logging required.

**REFRAMED per Round-1 C-3:** Mechanism-conditional framing. AMD-2 is NOT "intentionally modified" by default — it's preserved under H2 (the default). It's only superseded under H1 (last-resort) or on the H4 fallback path.

**Verified at:** S2a close-out. **A-class halt A10** fires if mechanism breaks DEC-117 atomic-bracket invariants.

**Sessions responsible:** S2a (establishes); S2b (preserves modification across other surfaces); S5a (validates end-to-end).

**Specific edges:**
- AMD-8 guard ("complete no-op if `_flatten_pending` already set") UNCHANGED across all mechanisms.
- AMD-4 guard ("no-op if `shares_remaining ≤ 0`") UNCHANGED across all mechanisms.
- AMD-2 framing (preserved/mixed/superseded) documented in DEC-390 with rationale for chosen mechanism.
- RSK-DEC-390-AMEND filed at sprint-close if H2 selected.
- RSK-DEC-390-CANCEL-AWAIT-LATENCY filed at sprint-close if H1 or H4 (with H1 fallback path possible).
- RSK-DEC-390-FINGERPRINT filed at sprint-close (regardless of mechanism selection).

---

### 18. Spike Artifacts Committed and Fresh at First Post-Merge Paper Session

**Test:** Operational regression. Before the first post-Sprint-31.92-seal paper session boots:
- `scripts/spike-results/spike-def204-round2-path1-results.json` exists, has `status: PROCEED`, dated within 30 days, includes `adversarial_axes_results`, `worst_axis_wilson_ub`, `h1_propagation_n_trials=100`, `h1_propagation_zero_conflict_in_100: bool` (per Decisions 1 + 2).
- `scripts/spike-results/spike-def204-round2-path2-results.json` exists, has `status: PROCEED`, dated within 30 days.
- `scripts/spike-results/sprint-31.92-validation-path1.json` exists, has `path1_safe: true`, dated post-S5a-merge.
- `scripts/spike-results/sprint-31.92-validation-path2.json` exists, has `path2_suppression_works: true` AND `broker_verification_at_timeout_works: true`, dated post-S5b-merge.
- `scripts/spike-results/sprint-31.92-validation-composite.json` exists, has composite-test pass criteria met, dated within 24 hours via daily CI.

**Verified at:** Sprint-close (D14 doc-sync) AND before each subsequent paper session for 30 days post-seal. **A-class halt A13** fires if any artifact >30 days old at any future trigger event (live-transition consideration, `ib_async`/IBKR Gateway upgrade).

**Sessions responsible:** S1a (path1 spike), S1b (path2 spike), S5a (path1 validation), S5b (path2 + composite validation), S5c (cross-layer + Branch 4).

---

### 19. (NEW per Round-1 C-2) `is_reconstructed = True` Refusal Posture Holds for All ARGUS-Emitted SELL Paths

**Test:** New regression test `test_restart_during_active_position_refuses_argus_sells` (S5b, AC5.4) — fixture: spawn ManagedPosition normally, partial-fill via T1, simulate restart by calling `reconstruct_from_broker()` (or directly setting `is_reconstructed=True` if test architecture requires), assert subsequent `_trail_flatten`, `_flatten_position`, `_check_flatten_pending_timeouts`, `_escalation_update_stop` invocations all refuse to emit SELL.

**Plus** unit-level `test_reconstruct_from_broker_initializes_is_reconstructed_true_and_zero_counters` (S5b) — asserts the single-line addition in `reconstruct_from_broker` correctly sets the flag.

**Verified at:** S5b close-out. **A-class halts A15 + A16** fire if violated in test OR in production paper trading.

**Sessions responsible:** S4a-i (establishes the field + ceiling-check short-circuit); S5b (regression test for refusal posture across all 4 standalone-SELL paths).

**Specific edges:**
- Field is in-memory only (NOT persisted to SQLite).
- Set ONLY in `reconstruct_from_broker` (single-line addition allowed inside the function body per SbC §"Do NOT modify").
- Refusal applies to ARGUS-emitted SELLs ONLY; operator-manual flatten via `scripts/ibkr_close_all_positions.py` is the only closing mechanism until Sprint 31.94 D3.
- RSK-RECONSTRUCTED-POSITION-DEGRADATION rated **MEDIUM-HIGH** per Severity Calibration Rubric (operator daily-flatten empirically failed Apr 28 — 27 of 87 ORPHAN-SHORT detections from a missed run; per H-R2-3). Sprint Abort Condition #7 trigger lowered from 4 weeks to 2 weeks. Time-bounded by Sprint 31.94 D3.

---

### 20. (NEW per Round-1 C-1) Pending-Reservation State-Transition Completeness

**Test:** Composite of S4a-i unit tests covering all 5 state transitions enumerated in AC3.1:
- `test_cumulative_pending_increments_synchronously_before_await` — asserts pending counter incremented BEFORE the `await place_order(...)` yield-point (the synchronous-before-await invariant is the architectural correctness contract).
- `test_cumulative_pending_decrements_on_cancel_reject` — order rejected/cancelled in `place_order` exception handler OR `cancel_order` confirmation: pending decrements.
- `test_cumulative_pending_transfers_to_sold_on_partial_fill` — partial fill: pending decrements by `filled_qty`, sold increments by `filled_qty`; remainder stays in pending.
- `test_cumulative_pending_transfers_to_sold_on_full_fill` — full fill: pending decrements by remaining, sold increments by remaining.
- `test_concurrent_sell_emit_race_blocked_by_pending_reservation` — **CANONICAL C-1 RACE TEST** (AC3.5).

**Verified at:** S4a-i close-out specifically; S4a-ii extends with AST-level regression (see invariant 23); S5b composite re-exercises in integration. **A-class halt A11** fires if any state transition leaks or under-decrements (e.g., pending counter drifts upward over session).

**Sessions responsible:** S4a-i (establishes all 5 state transitions); S4a-ii (AST-level regression scope extension to all bookkeeping callback paths); S5b (integration verification under load).

**Specific edges:**
- `cumulative_pending_sell_shares` is in-memory only (NOT persisted; per SbC §"Out of Scope" #21 — DEF-209 deferred).
- Synchronous-before-await ordering in code is load-bearing; reviewer must inspect diff for ordering violations.
- Cancel/reject paths must decrement (not just the success/fill paths).
- The H-R2-1 atomic `_reserve_pending_or_fail()` synchronous method is the place-time entry point; invariant 23 extends the AST guard to all other bookkeeping callbacks.

---

### 21. (NEW per Round-1 H-3) Broker-Verification Three-Branch Coverage at Suppression Timeout

**Test:** Three S3b tests covering AC2.5's three branches (post-refresh-success):
- `test_suppression_timeout_broker_shows_zero_logs_info_no_alert` — broker returns no entry for symbol; INFO log; no alert.
- `test_suppression_timeout_broker_shows_expected_long_logs_info_no_alert` — broker returns BUY-side entry with shares ≥ `position.shares_remaining`; INFO log; no alert.
- `test_suppression_timeout_broker_shows_unexpected_state_emits_alert` — broker returns short OR quantity divergence OR unknown side; publishes `phantom_short_retry_blocked` per DEC-385.

**Plus** Branch 4 / refresh-failure regression (see invariant 25 below for the dedicated Branch 4 invariant + HALT-ENTRY coupling per Tier 3 item C).

**Verified at:** S3b close-out. **A-class halt B12** fires if broker-verification logic fails in test OR production.

**Sessions responsible:** S3b.

**Specific edges:**
- Helper logic lives inline in `_check_flatten_pending_timeouts` housekeeping loop OR as a private method on OrderManager (NOT a new module — per SbC §"Do NOT add").
- `Broker.refresh_positions(timeout_seconds=5.0)` is the new ABC method introduced at S3b (per C-R2-1) and called BEFORE `broker.get_positions()`.
- `broker.get_positions()` call latency budget ≤ 200ms p95 per Performance Benchmarks; full refresh-then-verify path budgeted at ≤ 5.2s p95 worst case.
- Verification-failure fallback path (Branch 4) must NOT silently absorb the alert — operator-triage signal preserved via `verification_stale: true` metadata flag (see invariant 25).

---

### 22. (NEW per Round-1 C-3) Mechanism-Conditional Operator-Audit Logging Per AC1.6

**Test:** Conditional regression test (only if H1 or H4 selected at S1a):
- `test_path1_operator_audit_log_emitted_on_amd2_supersede` — asserts structured log line with required keys (`event`, `symbol`, `position_id`, `mechanism`, `cancel_propagation_ms`) fires when mechanism dispatches to H1 cancel-and-await branch (either as last-resort under H1 OR as fallback under H4).

**Verified at:** S2a close-out (if H1 or H4 selected); S2b close-out (extends to emergency-flatten branch).

**Sessions responsible:** S2a, S2b (conditional on S1a selection).

**Specific edges:**
- Log line must use canonical structured-log format (the existing ARGUS logger pipeline) — operator-visible.
- `mechanism` field discriminates `"h1_cancel_and_await"` (last-resort) from `"h4_fallback"` (hybrid fallback path).
- If H2 selected (default), this invariant is N/A — no AMD-2 supersede event ever fires.

---

### 23. (NEW per Tier 3 item A + B + Decision 3) Synchronous-Update Invariant on All Bookkeeping Callback Paths + Reflective-Pattern AST Coverage

**Test:** New regression file `tests/execution/order_manager/test_def204_callback_atomicity.py` (~120 LOC, 7 tests, S4a-ii):

- `test_no_await_in_reserve_pending_or_fail_body` — AST-no-await scan on `_reserve_pending_or_fail`. Reference implementation pattern (from S4a-i invariant 13 / 20).
- `test_no_await_between_bookkeeping_read_and_write_in_on_fill` — AST-no-await scan on `on_fill` partial-fill transfer path AND full-fill transfer path. Asserts `cumulative_pending_sell_shares` decrement and `cumulative_sold_shares` increment occur synchronously between the read and the write — no `await` between.
- `test_no_await_between_decrement_in_on_cancel` — AST-no-await scan on `on_cancel` decrement path.
- `test_no_await_between_decrement_in_on_reject` — AST-no-await scan on `on_reject` decrement path.
- `test_no_await_in_on_order_status_bookkeeping_mutations` — AST-no-await scan on `_on_order_status` paths that mutate `cumulative_pending_sell_shares` or `cumulative_sold_shares`.
- `test_no_await_in_check_sell_ceiling_multi_attribute_read` — AST-no-await scan on `_check_sell_ceiling`'s multi-attribute read sequence (the read of `cumulative_pending_sell_shares` + `cumulative_sold_shares` + `shares_total` + `is_reconstructed` must happen without an intervening `await`).
- **Plus** mocked-await injection regression: monkey-patch each path to insert `await asyncio.sleep(0)` between read and write; assert the race IS observable under injection.

**Plus** the H-R2-5 reflective-pattern sub-tests on AST callsite scan (existing invariant 24 reframed as AST guard for `is_stop_replacement=True` callers). Three reflective-pattern coverage tests (FAI #8 option (a) per Decision 3):
- `test_ast_callsite_scan_catches_kw_unpacking` — synthetic call site `_check_sell_ceiling(**{"is_stop_replacement": True, ...})`; AST scan must flag.
- `test_ast_callsite_scan_catches_computed_value_flag_assignment` — synthetic call site `flag = compute_flag(); _check_sell_ceiling(is_stop_replacement=flag)`; AST scan must flag.
- `test_ast_callsite_scan_catches_getattr_reflective_access` — synthetic call site `getattr(om, '_check_sell_ceiling')(is_stop_replacement=True)`; AST scan must flag.

**REWRITTEN per Tier 3 items A + B + Decision 3 / FAI entries #8 + #9:** The H-R2-1 atomic-reserve protection pattern is the reference implementation; the same AST guard + injection test apply to every callback path that mutates the bookkeeping counters. The L3 ceiling correctness depends on the asyncio single-event-loop guarantee applying to every path that mutates these counters, not only `_reserve_pending_or_fail`. Reflective-call coverage closes FAI #8.

**Verified at:** S4a-ii close-out. **A-class halt A11** fires if false-positives in production paper trading trace to a callback-path leak (i.e., the callback-path AST guard caught nothing in test but production exhibited a race).

**Sessions responsible:** S4a-ii (establishes the AST regression infrastructure + reflective-pattern coverage); S4a-i (establishes the reference implementation in `_reserve_pending_or_fail`); S5b (integration stress under load); S5c CL-1 (cross-layer composition: force `_reserve_pending_or_fail` false-positive, ceiling catches at reconciliation).

**Specific edges:**
- Preferred outcome of S4a-ii is **zero production-code change** with the test file establishing the regression guard. If static-analysis reveals an existing await between bookkeeping read and write, fix is in-scope for S4a-ii.
- Decision 3 explicitly chose option (a) over option (b) (accept-and-document NOT taken).
- DEF-FAI-CALLBACK-ATOMICITY (Tier 3 verdict; sprint-gating Round 3 advancement) — closure of this DEF requires invariant 23 to be active and green at S4a-ii close-out.
- DEF-FAI-8-OPTION-A (Tier 3 verdict; Sprint 31.92 S4a-ii) — closure requires the 3 reflective-pattern sub-tests above to be active and green.

---

### 24. (NEW per Tier 3 item C) `halt_entry_until_operator_ack=True` Posture Fires Under H1 Active + Refresh Failure

**Test:** New regression tests in `tests/execution/order_manager/test_def204_round2_path2.py` (extended at S3b):

- `test_halt_entry_fires_under_h1_active_and_refresh_timeout` — with H1 selected as active mechanism (mock `selected_mechanism="h1_cancel_and_await"`) AND `Broker.refresh_positions()` raising `asyncio.TimeoutError`, assert `position.halt_entry_until_operator_ack == True` after Branch 4 fires.
- `test_halt_entry_fires_under_h1_active_and_refresh_raises` — same but `refresh_positions()` raises arbitrary exception (e.g., `ConnectionError`).
- `test_halt_entry_does_NOT_fire_under_h2_active_and_refresh_timeout` — with H2 selected, refresh failure publishes Branch 4 alert with `verification_stale: true` metadata BUT does NOT mark `halt_entry_until_operator_ack`. (H1-specific coupling per Tier 3 item C.)
- `test_halt_entry_does_NOT_fire_under_h4_amend_success_and_refresh_timeout` — with H4 selected and amend-success path active, refresh failure does NOT mark halt-entry.
- `test_halt_entry_blocks_subsequent_sell_attempts_on_position` — once `halt_entry_until_operator_ack=True` is set, all subsequent `_trail_flatten`, `_flatten_position`, `_check_flatten_pending_timeouts`, `_escalation_update_stop` invocations on the position refuse to emit SELL.

**NEW per Tier 3 item C / C-R2-1↔H-R2-2 coupling:** Without this coupling, FAI #2 + FAI #5 compound when H1 is selected against a stale broker cache. The HALT-ENTRY posture is the structural defense.

**Verified at:** S3b close-out. **A-class halt A17** fires if Branch 4 fires + H1 active without HALT-ENTRY firing in test OR in production.

**Sessions responsible:** S3b (establishes); S5c CL-3 (cross-layer composition: force refresh timeout AND H1 selection; verify HALT-ENTRY catches the composite using `SimulatedBrokerWithRefreshTimeout` fixture).

**Specific edges:**
- `position.halt_entry_until_operator_ack: bool = False` is a NEW in-memory `ManagedPosition` field (4th field added by this sprint; threading documented in S3b).
- Operator-driven resolution: no automatic recovery; operator must explicitly clear the flag (out-of-scope for Sprint 31.92 — operator-manual via existing administrative path).
- No further SELL attempts on the position; no phantom short.
- AC2.5 Branch 4 always publishes the `phantom_short_retry_blocked` alert with `verification_stale: true` metadata — the HALT-ENTRY posture is an additional state mutation conditional on H1 active.

---

### 25. (NEW per Tier 3 item E + Decision 5) Branch 4 (`verification_stale: true`) Fires on `Broker.refresh_positions()` Failure + `SimulatedBrokerWithRefreshTimeout` Fixture Coverage

**Test:** Two test paths cover Branch 4:

1. **Direct unit test** in `tests/integration/test_def204_round2_validation.py` (S5c, ~1 test using fixture):
   - `test_branch_4_fires_on_refresh_timeout_with_simulated_fixture` — uses `SimulatedBrokerWithRefreshTimeout` from `tests/integration/conftest_refresh_timeout.py`. Assert: when `refresh_positions()` exceeds `timeout_seconds`, alert is published with `verification_stale: True` metadata + `verification_failure_reason: "TimeoutError"` + `position_id` + `symbol`. Locate-suppression dict entry for the position is NOT cleared.
2. **Cross-layer composition** CL-3 (see invariant 27).

**NEW per Tier 3 item E + Decision 5 / DEF-SIM-BROKER-TIMEOUT-FIXTURE:** Currently `SimulatedBroker.refresh_positions()` is no-op or instant-success; in-process tests cannot exercise Branch 4 without the fixture variant. The `SimulatedBrokerWithRefreshTimeout` fixture (S5c, `tests/integration/conftest_refresh_timeout.py`, ~80 LOC) subclasses `SimulatedBroker` and overrides `refresh_positions()` to raise `asyncio.TimeoutError` after a configurable delay.

**Verified at:** S5c close-out. **B-class halt B12** fires if Branch 4 fails to emit OR emits with wrong metadata.

**Sessions responsible:** S3b (establishes Branch 4 logic in production code per AC2.5); S5c (establishes the fixture + the dedicated Branch 4 unit test); S5c CL-3 (cross-layer composition).

**Specific edges:**
- The fixture lives ONLY in test code (`tests/integration/conftest_refresh_timeout.py`). Production `SimulatedBroker` is NOT modified (preserves SbC §"Do NOT modify" #2).
- Fixture is held to ≤80 LOC to avoid the large-file compaction penalty per S5c scoring.
- DEF-SIM-BROKER-TIMEOUT-FIXTURE (Tier 3 verdict; Sprint 31.92 S5c) — closure of this DEF requires this invariant active and green at S5c close-out.

---

### 26. (NEW per Decision 4) AC2.7 `_pending_sell_age_seconds` Watchdog Auto-Activation From `auto` to `enabled` on First `case_a_in_production` Event

**Test:** S3a + S4a-i regression tests in `tests/execution/order_manager/test_def204_round2_path2.py` and (state-transition test) in `tests/execution/order_manager/test_def204_round2_ceiling.py`:

- `test_pending_sell_age_watchdog_enabled_field_pydantic_validation` — `OrderManagerConfig.pending_sell_age_watchdog_enabled` accepts `"auto"`, `"enabled"`, `"disabled"` values; rejects others.
- `test_pending_sell_age_watchdog_default_is_auto` — config default is `"auto"`.
- `test_pending_sell_age_watchdog_auto_flips_to_enabled_on_case_a_event` — synthetic `case_a_in_production` event (production paper-session emit) flips the runtime state from `auto` to `enabled`. Recorded for sprint-close pre-live transition checklist (see C9 in `doc-update-checklist.md`).
- `test_pending_sell_age_watchdog_disabled_does_not_fire` — when set to `disabled`, watchdog does not fire even on aged pending positions.
- `test_pending_sell_age_watchdog_enabled_fires_on_aged_pending` — when set to `enabled`, watchdog fires when `now - position.last_sell_emit_time > pending_sell_age_seconds` AND no fill observed.

**NEW per Decision 4 (M-R2-1 strengthening):** The watchdog provides the structural fallback for any unmodeled locate-rejection string variant (FAI #4 mitigation). `auto` mode flips to `enabled` on first observed `case_a_in_production` event — NOT manual operator activation per Decision 4.

**Verified at:** S3a close-out (Pydantic field validation); S4a-i close-out (auto-activation logic); production observation post-merge (informational A-class trigger A18 — see escalation criteria).

**Sessions responsible:** S3a (establishes Pydantic field); S4a-i (establishes auto-activation logic).

**Specific edges:**
- Field default `"auto"` is fail-conservative — if the operator never touches the config, the watchdog activates on first need.
- Auto-flip is a one-way state transition (auto → enabled); no auto-deactivation. Operator must manually flip back to `disabled` if desired.
- Auto-flip event is logged as a structured INFO log line (operator-visible) AND recorded as runtime state for pre-live-transition checklist purposes.

---

### 27. (NEW per Decision 5) 5 Cross-Layer Composition Invariants — CL-1 through CL-5

**Test:** 5 cross-layer composition tests in `tests/integration/test_def204_round2_validation.py` (extended at S5c, ~5 tests + 1 Branch 4 unit test from invariant 25 = 6 net new tests at S5c). Each test by definition slow + ugly + spans multiple modules per `templates/sprint-spec.md` v1.2.0 § Defense-in-Depth Cross-Layer Composition Tests.

The 5 tests:

1. **CL-1 (L1 fails → L3 catches):** `test_l1_reserve_false_positive_caught_by_l3_ceiling` — Force `_reserve_pending_or_fail` false positive (mock the synchronous method to return True even when the ceiling would be exceeded). Verify the ceiling-violation invariant catches at reconciliation; locate-suppression-with-broker-verification alert path fires.

2. **CL-2 (L4 fails → L2 catches):** `test_l4_rollback_does_not_disable_l2_ceiling_on_emergency_flatten` — Force startup with `bracket_oca_type != 1` AND `--allow-rollback` (the operator-confirmed rollback path). Verify under DEC-386 rollback that the emergency-flatten branch (Layer 2 via `is_stop_replacement=False`) still ceiling-checks; this proves Layer 2 doesn't depend on Layer 4's enforcement.

3. **CL-3 (L3 + L5 cross-falsification — FAI #2 + #5 + Tier 3 item C):** `test_h1_active_plus_refresh_timeout_caught_by_halt_entry` — Force `Broker.refresh_positions()` timeout (using `SimulatedBrokerWithRefreshTimeout` fixture per invariant 25 / DEF-SIM-BROKER-TIMEOUT-FIXTURE) AND H1 selection by S1a output. Verify the H-R2-2 HALT-ENTRY posture catches the composite — position marked `halt_entry_until_operator_ack=True`; no further SELL attempts; no phantom short.

4. **CL-4 (L1 + L2; NEW per Tier 3 sub-area D):** `test_misclassified_stop_replacement_caught_by_l3_ceiling` — Reservation succeeds but `is_stop_replacement` decision is wrong (e.g., emergency-flatten misclassified as stop-replacement); verify L3 ceiling catches the resulting over-flatten.

5. **CL-5 (L2 + L3; NEW per Tier 3 sub-area D):** `test_protective_stop_replacement_with_locate_suppression_does_not_false_fire_branch_4` — `is_stop_replacement` correctly disambiguates a stop-replacement (L2 grants exemption) AND locate-suppression for the position is active. Verify the protective stop-replacement path is allowed AND that Branch 4 does not falsely fire on it.

**CL-6 (rollback + locate-suppression interaction) is OUT of scope per Decision 5** — deferred with rationale documented in `docs/process-evolution.md`. L4's compositions with runtime layers (other than CL-2) are weakly meaningful in the operationally-relevant case; the trade-off between exhaustive coverage and bounded session count was resolved in favor of bounded scope at this sprint.

**NEW per Decision 5 + Tier 3 item E:** Per `templates/sprint-spec.md` v1.2.0 (mandatory when DEC entries claim N≥3 layer defense), DEC-390's 4-layer structure activates the cross-layer requirement. Sprint 31.92 commits to 5 tests (above the template's "at least one" floor; above Tier 3's 3-test floor).

**Verified at:** S5c close-out. **A-class halt A17** triggers on CL-3 failure specifically (sub-class of "Branch 4 fires + H1 active without HALT-ENTRY firing"). General CL-1/CL-2/CL-4/CL-5 failure surfaces via Tier 2 verdict at S5c.

**Sessions responsible:** S5c (establishes all 5 tests).

**Specific edges:**
- CL-3 uses the `SimulatedBrokerWithRefreshTimeout` fixture per invariant 25.
- CL-2 stresses bracket atomic invariants under L4 rollback (composes with invariants 1 + 6 + 16).
- CL-5 must explicitly verify Branch 4 does NOT fire on a legitimate stop-replacement path (no false-positive in cross-layer composition).
- DEF-CROSS-LAYER-EXPANSION (Tier 3 verdict; Sprint 31.92 — 5 CL tests delivered, CL-6 deferred) — closure requires this invariant active and green at S5c close-out.
- Cross-layer tests are typically slow, ugly, and span multiple modules. That is the cost of catching composition failures structurally rather than relying on per-layer tests alone.

---

### 28. (NEW per Round 3 C-R3-1) `Broker.refresh_positions()` Body Wrapped in Single-Flight `asyncio.Lock` + 250ms Coalesce Window

**Test:** `tests/execution/test_ibkr_broker_concurrent_callers.py` (NEW file at S3b) exercises N=20 concurrent coroutines calling `IBKRBroker.refresh_positions()` near-simultaneously (≤10ms separation) with mocked-await injection between A's `reqPositions()` and B's `reqPositions()` and a deterministic broker-state-change between callers; asserts the race IS observable WITHOUT the single-flight serialization mitigation AND is NOT observable WITH the mitigation enabled.

**Verified at:** S3b close-out (sub-spike for FAI #10) AND S5c CL-7 (cross-layer composition).

**Sessions responsible:** S3b (establishes the single-flight wrapper + concurrent-caller regression test); S5c (extends with CL-7 cross-layer composition).

**Specific edges:**
- The 250ms coalesce window is bounded; coroutine B that arrives more than 250ms after coroutine A's cache-synchronization timestamp performs its own broker round-trip rather than coalescing.
- Coalesce window applies only to successive callers within the window; concurrent callers at the same instant serialize via the lock.
- Sprint Abort Condition (NEW per Round 3 C-R3-1) fires if Fix A spike fails AND no alternative serialization design surfaces.

---

### 29. (NEW per Round 3 H-R3-5) Bookkeeping Callsite-Enumeration AST Exhaustiveness

**Test:** `test_bookkeeping_callsite_enumeration_exhaustive` (S4a-ii regression scope, ~40 LOC) — AST scan walks `OrderManager`'s source for `ast.AugAssign` nodes targeting `cumulative_pending_sell_shares` or `cumulative_sold_shares`; finds the enclosing function name for each; asserts the set of enclosing functions is a subset of the FAI #9 protected callsite list (`_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, `_check_sell_ceiling` multi-attribute read, `reconstruct_from_broker` initialization). Falsifies if a mutation site exists outside the expected list.

**Verified at:** S4a-ii close-out.

**Sessions responsible:** S4a-ii.

**Specific edges:**
- FAI #11 falsification gate: the test must fail when a new mutation site is introduced that isn't added to the FAI #9 protected list.
- Resolution if falsified: extend the FAI #9 protected scope to include the discovered callsite (preferred) or document the coverage gap with explicit rationale.

---

### 30. (NEW per Round 3 M-R3-4) `refresh_positions`-then-`get_positions` Helper + AST-No-Await Scan Extension

**Test:** AST-no-await scan extended to `_read_positions_post_refresh()` helper body at S4a-ii — asserts no `ast.Await` between `refresh_positions` invocation completion and `get_positions` cache read. Per M-R3-4 fix shape, the helper composes both calls into a single synchronous read-after-refresh sequence, removing yield-gap-between-refresh-and-read class of races.

**Verified at:** S4a-ii close-out.

**Sessions responsible:** S3b (introduces helper at AC2.5 fallback site); S4a-ii (AST-no-await scan extension).

**Specific edges:**
- The helper is the single entry point for all refresh-then-read sequences in OrderManager; AC2.5 fallback paths use it instead of calling the two-step sequence directly.
- Performance budget per spec § Performance Benchmarks: ≤5µs per-call overhead.

---

### 31. (NEW per Round 3 H-R3-1) `time.monotonic()` at All Suppression-Timeout Sites

**Test:** `test_locate_suppression_resilient_to_wall_clock_skew` (S3b regression scope) — fixture sets up locate-suppression entry, then advances synthetic wall-clock by injecting a backwards jump (e.g., NTP correction during session), then asserts suppression-timeout calculation correctly reflects monotonic time elapsed rather than wall-clock delta.

**Verified at:** S3b close-out (test fixture); ongoing CI green.

**Sessions responsible:** S3b (introduces `time.monotonic()` at all 4 standalone-SELL exception handlers + AC2.5 timeout-check site).

**Specific edges:**
- All 4 standalone-SELL exception handlers + the AC2.5 timeout-check site use `time.monotonic()`, not `time.time()`.
- `OrderManagerConfig.locate_suppression_seconds` validator footnote per § 7.1 Config Changes: bounds (300–86400) are seconds in monotonic time; equivalent to wall-clock under normal operation.

---

### 32. (NEW per Round 3 H-R3-3) RiskManager Check 0 Halt-Entry Extension + Ack Mechanism

**Test:** Two regression tests at S3b:
- `test_risk_manager_check0_rejects_when_halt_entry_set` — instantiate ManagedPosition with `halt_entry_until_operator_ack=True`; emit entry signal for the SAME `ManagedPosition.id`; assert RiskManager rejects via Check 0 with reason="halt_entry_set"; assert per-position granularity preserved (new positions on same symbol unaffected).
- `test_clear_halt_endpoint_requires_position_id_and_clears_flag` — call `POST /api/v1/positions/{position_id}/clear_halt` with valid + invalid position IDs; assert valid clears the flag and emits `event="halt_entry_cleared"` log; invalid returns 404.

**Verified at:** S3b close-out.

**Sessions responsible:** S3b (extends RiskManager Check 0); separate sub-session within S3b implements the REST endpoint + CLI tool (`scripts/clear_position_halt.py`).

**Specific edges:**
- Per AC2.8: halt-entry flag does NOT survive restart; `is_reconstructed=True` posture (AC3.7) subsumes halt-entry by refusing ALL ARGUS-emitted SELLs on reconstructed positions.
- Per-position granularity: only the SAME `ManagedPosition.id` is affected; new positions on the same symbol bypass the halt.

---

### 33. (NEW per Round 3 H-R3-4) Interactive Ack at Startup + CI-Override Flag Separation

**Test:** Three regression tests at S4b:
- `test_startup_interactive_ack_required_when_rollback_active_and_tty` — instantiate ARGUS startup with `bracket_oca_type=0` AND `--allow-rollback` AND TTY-detected; mock stdin to provide exact phrase "I ACKNOWLEDGE ROLLBACK ACTIVE"; assert ARGUS proceeds.
- `test_startup_exits_3_when_rollback_active_and_tty_and_wrong_phrase` — same setup with stdin providing wrong phrase; assert exit code 3.
- `test_startup_skip_confirm_flag_bypasses_interactive_ack_for_ci` — `--allow-rollback-skip-confirm` flag present + `bracket_oca_type=0` + `--allow-rollback` flag present; assert ARGUS proceeds without prompt; assert canonical-logger CRITICAL emission still fires (CI evidence trail preserved).

**Verified at:** S4b close-out.

**Sessions responsible:** S4b.

**Specific edges:**
- Per Round 3 H-R3-4: `--allow-rollback-skip-confirm` is separate from `--allow-rollback`; production startup MUST require interactive ack (per SbC §19, NEW).
- Periodic re-ack every 4 hours: separate test (`test_periodic_reack_emits_every_4h_when_rollback_active`) verified via mock-time advance.

---

### 34. (NEW per Round 3 M-R3-2) Branch 4 Alert Throttling — 1-Hour Per-Position Cooldown

**Test:** `test_branch_4_throttle_one_per_hour_per_position` (S3b regression scope) — fire Branch 4 twice on the same `ManagedPosition.id` within 1-hour window; assert first firing publishes `phantom_short_retry_blocked` alert; second firing is suppressed at alert layer (logged INFO with `branch_4_throttled: true`); assert HALT-ENTRY effect persists across both firings; advance synthetic clock past 1-hour window AND fire third Branch 4; assert third firing publishes alert again.

**Verified at:** S3b close-out.

**Sessions responsible:** S3b (introduces Branch 4 throttle).

**Specific edges:**
- Throttle resets on `on_position_closed` OR successful refresh observation (whichever fires first).
- Throttling is at alert layer only — HALT-ENTRY effect persists; the throttle does NOT silently drop the safety property.

---

**Total invariants:** 27 (Round 2 baseline) + 7 (Round 3) = **34**.

---

## Per-Session Verification Matrix

The matrix below shows which invariants each session's `@reviewer` MUST explicitly verify in the Tier 2 verdict. **13 sessions total** (was 10 pre-Tier-3): S1a + S1b spikes; S2a + S2b Path #1; S3a + S3b Path #2; S4a-i + S4a-ii (split per Tier 3 items A + B); S4b DEF-212 rider; S5a + S5b validation; S5c (NEW per Decision 5 + Tier 3 item E).

| Invariant | S1a | S1b | S2a | S2b | S3a | S3b | S4a-i | S4a-ii | S4b | S5a | S5b | S5c |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:-----:|:------:|:---:|:---:|:---:|:---:|
| 1. DEC-117 atomic bracket | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ✓ | ▢ | ✓ | ✓ | ✓ | ✓ |
| 2. DEC-364 cancel_all_orders no-args ABC | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ | ▢ |
| 3. DEC-369 broker-confirmed immunity | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ▢ | ▢ | ▢ | ✓ | ▢ |
| 4. DEC-372 stop retry caps + backoff | ▢ | ▢ | ▢ | ✓ | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ▢ |
| 5. DEC-385 6-layer side-aware reconciliation | ▢ | ▢ | ✓ | ✓ | ✓ | ✓ | ✓ | ▢ | ✓ | ✓ | ✓ | ✓ |
| 6. DEC-386 4-layer OCA architecture | ▢ | ▢ | ✓ | ✓ | ✓ | ✓ | ✓ | ▢ | ✓ | ✓ | ✓ | ✓ |
| 7. DEC-388 alert observability | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ▢ | ✓ | ✓ |
| 8. DEF-158 3-branch side-check verbatim | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ | ▢ | ▢ | ▢ | ▢ | ✓ | ▢ |
| 9. `# OCA-EXEMPT:` mechanism | ▢ | ▢ | ✓ | ✓ | ✓ | ✓ | ✓ | ▢ | ✓ | ✓ | ✓ | ✓ |
| 10. Test count ≥ baseline | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 11. Pre-existing flake count | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 12. Frontend immutability | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 13. SELL-volume ceiling (pending+sold pattern) | — | — | — | — | — | — | ✓ | ✓ | ▢ | ▢ | ✓ | ✓ |
| 14. Path #2 fingerprint + position-keyed dict + broker-verification | — | ✓ | — | — | ✓ | ✓ | — | — | — | — | ✓ | ✓ |
| 15. `_OCA_TYPE_BRACKET` constant deleted | — | — | — | — | — | — | — | — | ✓ | ✓ | ✓ | ✓ |
| 16. AC4.4 OCA-type lock-step (not validity) | — | — | — | — | — | — | — | — | ✓ | — | ▢ | ✓ |
| 17. AMD-2 mechanism-conditional | — | — | ✓ | ✓ | — | — | — | — | — | ✓ | ✓ | ▢ |
| 18. Spike artifacts fresh + committed | ✓ | ✓ | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ | ✓ |
| 19. `is_reconstructed` refusal posture | — | — | — | — | — | — | ✓ | ▢ | ▢ | ▢ | ✓ | ▢ |
| 20. Pending-reservation state transitions | — | — | — | — | — | — | ✓ | ✓ | ▢ | ▢ | ✓ | ▢ |
| 21. Broker-verification three-branch | — | — | — | — | — | ✓ | ▢ | ▢ | ▢ | ▢ | ✓ | ✓ |
| 22. Operator-audit logging (conditional) | — | — | ✓¹ | ✓¹ | — | — | — | — | — | ✓¹ | ✓¹ | ▢¹ |
| 23. **(NEW)** Synchronous-update invariant on all bookkeeping callback paths + reflective-pattern AST | — | — | — | — | — | — | ▢ | ✓ | ▢ | ▢ | ✓ | ✓ |
| 24. **(NEW)** `halt_entry_until_operator_ack=True` posture under H1 + refresh fail | — | — | — | — | — | ✓ | — | — | — | — | ▢ | ✓ |
| 25. **(NEW)** Branch 4 (`verification_stale: true`) + `SimulatedBrokerWithRefreshTimeout` fixture | — | — | — | — | — | ✓ | — | — | — | — | ▢ | ✓ |
| 26. **(NEW)** AC2.7 watchdog auto-activation (`auto` → `enabled` on first `case_a_in_production`) | — | — | — | — | ✓ | — | ✓ | — | — | — | ▢ | ▢ |
| 27. **(NEW)** 5 Cross-Layer Composition tests (CL-1 through CL-5) | — | — | — | — | — | — | — | — | — | — | — | ✓ |

**Legend:**
- ✓ = MANDATORY verification at this session's Tier 2 review.
- ▢ = SOFT verification (trust test suite unless suspicious diff).
- — = Not yet established.
- ✓¹ = MANDATORY only if S1a selected H1 or H4 (otherwise N/A).
- ▢¹ = SOFT verification, conditional on H1 or H4 selection.

---

## Cross-Session Invariant Risks

### Risk: `argus/execution/order_manager.py` Mass Modification

**Concern:** 8 of 13 sessions modify `order_manager.py` (S2a/S2b/S3a/S3b/S4a-i/S4a-ii/S4b/S5c). Cumulative diff at S5c will be substantial.

**Mitigation (revised per Round-1 + Tier 3):**
- DEC-328 tiering keeps full suite at every close-out → automated regression catches semantic breaks.
- Per-session structural-anchor edits (protocol v1.2.0+) keep diff hunks scoped.
- `git diff <session-base>..HEAD -- argus/execution/order_manager.py | wc -l` reported in every close-out for cumulative-diff tracking.
- Final review at S5c uses full suite + Tier 2 reviewer reads cumulative diff explicitly.
- **Cumulative diff bound recalibrated per Tier 3 guidance (2026-04-29):** **~1150–1300 LOC** for `order_manager.py` (was ~1100–1200 pre-Tier-3; +50 to +100 for callback-path AST guards per Tier 3 items A + B + Branch 4 coupling per Tier 3 item C + AC2.7 auto-activation per Decision 4 + `halt_entry_until_operator_ack` field threading per Tier 3 item C).

**Tracking:** Cumulative diff line count at each session close-out:

| Session | Expected Δ in `order_manager.py` | Cumulative Δ (bound) |
|---------|---------------------------------:|---------------------:|
| S2a | ~30–60 LOC | ~60 |
| S2b | ~40–80 LOC | ~140 |
| S3a | ~70–110 LOC (+ `pending_sell_age_watchdog_enabled` field per Decision 4) | ~250 |
| S3b | ~150–220 LOC (4 emit-site exception handlers + suppression-check + broker-verification fallback + Branch 4 + HALT-ENTRY coupling per Tier 3 item C + `halt_entry_until_operator_ack` field threading) | ~470 |
| S4a-i | ~160–220 LOC (3 ManagedPosition fields + on_fill state machine + `_reserve_pending_or_fail` atomic helper + `_check_sell_ceiling` + 5 guards + reconstruct_from_broker line + POLICY_TABLE + AC2.7 auto-activation logic) | ~690 |
| S4a-ii | ~0–30 LOC (preferred outcome: zero production-code change; ≤30 LOC if static-analysis reveals an existing await between bookkeeping read and write) | ~720 |
| S4b | ~15–25 LOC (4 substitutions + constant deletion + `__init__` signature + dual-channel warning + `--allow-rollback` flag check) | ~745 |
| S5c | ~0 LOC (test-only — fixture + 5 CL tests + 1 Branch 4 unit test) | ~745 |

**Soft cap:** ~1300 cumulative LOC (was ~1000 pre-Tier-3). Anything beyond suggests scope creep → Tier 2 reviewer flags.

### Risk: Path #1 Mechanism Choice Cascading

**Concern:** S2a's H2/H4/H1 selection cascades into S2b (other surfaces), S5a (validation fixture), AMD-2 invariant framing (regression test renaming + DEC-390 documentation), conditional operator-audit logging (invariant 22), and CL-3 (cross-layer composition under H1 specifically per invariant 27).

**Mitigation (revised per Round-1 + Tier 3):**
- S2a close-out documents the chosen mechanism explicitly in a "Mechanism Selected" section.
- S2b's pre-flight reads S2a close-out + `scripts/spike-results/spike-def204-round2-path1-results.json` and asserts mechanism consistency.
- S5a's fixture is mechanism-agnostic (asserts AC1.1 `total_sold ≤ shares_total` regardless of HOW the mechanism prevents over-flatten).
- DEC-390 entry template (in `doc-update-checklist.md` C2) has placeholders for mechanism choice.
- **Operator-audit logging (invariant 22) is conditional on H1/H4 selection** — S2a impl prompt branches on the JSON `selected_mechanism` field.
- **CL-3 (invariant 27) requires H1 to be the active mechanism for the HALT-ENTRY posture verification.** If H2 is selected, CL-3 still runs but mocks `selected_mechanism="h1_cancel_and_await"` to exercise the coupling code path.
- **Decision 2 N=100 hard gate** — even if `modifyOrder` Wilson UB is favorable for H2, H1 is NOT eligible if `h1_propagation_zero_conflict_in_100 == false`. This shifts mechanism selection logic toward H2/H4.

**Tracking:** Sprint-close DEC-390 entry must explicitly cite the mechanism selected (not "one of H2/H4/H1" — the actual choice). RSK filing at sprint-close conditional on mechanism (RSK-DEC-390-AMEND for H2; RSK-DEC-390-CANCEL-AWAIT-LATENCY for H1 or H4-with-fallback-active).

### Risk: Validation Artifact Drift

**Concern:** S5a + S5b commit JSON artifacts under `scripts/spike-results/`. Composite artifact specifically uses Pytest-side-effect pattern with daily CI freshness.

**Mitigation (revised per Round-1 M-3 + Phase B re-run):**
- Invariant 18 establishes 30-day freshness check for spike + path1 + path2 artifacts.
- Composite artifact freshness: daily CI workflow runs the test and updates mtime. If CI workflow misconfigured or failing silently, freshness check at A13 catches at first post-merge paper session.
- Pytest test `test_validate_path{1,2}_artifact_committed_to_repo` (S5a + S5b) asserts artifact exists at expected path with valid schema.
- **NEW per Phase B re-run / pre-live transition checklist additions (see `doc-update-checklist.md` C9):** "Spike artifact freshness ≤30 days" gate; "daily composite test green ≥7 days content-AND-mtime"; pre-live transition checklist additions enforce both content AND mtime requirements.
- Quarterly operational re-validation flagged in `docs/risk-register.md`.

**Tracking:** Sprint-close establishes baseline; sprint-history.md records artifact mtimes/SHAs.

### Risk: `is_reconstructed` Refusal Posture Operational Degradation

**NEW per Round-1 C-2 disposition; severity ESCALATED per Phase B Severity Calibration Rubric application.**

**Concern:** Reconstructed positions accumulate operational state during paper trading; operator daily-flatten infrastructure must keep up; any failure of operator-manual flatten leaves capital trapped.

**Mitigation:**
- A-class halt A16 fires if operational degradation observed.
- Sprint Abort Condition #7 covers sustained degradation across multiple paper sessions; **trigger lowered from 4 weeks to 2 weeks per H-R2-3 + Severity Calibration Rubric** (operator daily-flatten empirically failed Apr 28 — 27 of 87 ORPHAN-SHORT detections from a missed run).
- RSK-RECONSTRUCTED-POSITION-DEGRADATION filed at sprint-close (severity **MEDIUM-HIGH**, time-bounded by Sprint 31.94 D3).
- Sprint 31.94 D3 (boot-time adoption-vs-flatten policy) eliminates the conservative posture; this risk is structurally bounded.

**Tracking:** Sprint-close RSK + Sprint 31.94 D3 inheritance pointer.

### Risk: Synchronous-Update Invariant Scope Gap (NEW per Tier 3 item A + B)

**Concern:** Tier 3 verdict identified that the H-R2-1 atomic-reserve protection pattern was previously scoped to `_reserve_pending_or_fail` only. The L3 ceiling correctness depends on the asyncio single-event-loop guarantee applying to every path that mutates the bookkeeping counters, not only the place-time path. Without scope extension, the asyncio yield-gap race could re-emerge via callback paths (`on_fill`, `on_cancel`, `on_reject`, `_on_order_status`).

**Mitigation:**
- Invariant 23 establishes AST-no-await scan + mocked-await injection regression on ALL bookkeeping mutation paths AND on `_check_sell_ceiling`'s multi-attribute read.
- S4a-ii (NEW SESSION) is dedicated to building this regression infrastructure.
- Preferred outcome of S4a-ii is **zero production-code change** with the test file establishing the regression guard. If static-analysis reveals an existing await between bookkeeping read and write, fix is in-scope for S4a-ii.
- DEF-FAI-CALLBACK-ATOMICITY (Tier 3 verdict; sprint-gating Round 3 advancement) — closure of this DEF requires invariant 23 to be active and green at S4a-ii close-out.

**Tracking:** Sprint-close DEC-390 explicitly cites synchronous-update invariant scope per regression invariant 23.

### Risk: Reflective Call Pattern Coverage Gap (NEW per Decision 3 / FAI #8)

**Concern:** AST callsite scan for `is_stop_replacement=True` callers (existing invariant 24 / regression infrastructure) may have false-negative paths via reflective or aliased call patterns: `**kw` unpacking, computed-value flag assignment, `getattr` reflective access.

**Mitigation:**
- Invariant 23 includes 3 reflective-pattern sub-tests at S4a-ii (FAI #8 option (a) per Decision 3).
- Decision 3 explicitly chose option (a) over option (b) (accept-and-document NOT taken).
- DEF-FAI-8-OPTION-A (Tier 3 verdict; Sprint 31.92 S4a-ii) — closure requires the 3 reflective-pattern sub-tests active and green.

**Tracking:** S4a-ii close-out explicitly reports the 3 reflective-pattern test outcomes.

### Risk: Cross-Layer Composition Test Incompleteness (NEW per Decision 5)

**Concern:** Cross-layer composition test count at 5 (above template floor; below exhaustive). DEC-386's empirical falsification justifies heightened bar; CL-6 (rollback + locate-suppression interaction) explicitly deferred.

**Mitigation:**
- Invariant 27 + S5c deliver 5 CL tests (CL-1 through CL-5).
- CL-6 deferral rationale documented in `docs/process-evolution.md` (per `doc-update-checklist.md` C10).
- RSK-CROSS-LAYER-INCOMPLETENESS filed at sprint-close (severity **MEDIUM**; Tier 3 verdict 2026-04-29).

**Tracking:** Sprint-close RSK + `docs/process-evolution.md` lesson on CL test count rationale.

---

## Adversarial Review Round 3 Reference

The Adversarial Review Input Package Round 3 will include this Regression Checklist verbatim. **Round 3 is full scope per `protocols/adversarial-review.md` v1.1.0 § Outcome C** (supersedes the Round-2 disposition's narrowest-scope recommendation; the 2026-04-29 metarepo amendment binds Round 3 to full scope).

Reviewers should specifically scrutinize:

1. Whether 27 invariants is sufficient or if any A-class halt in `escalation-criteria.md` lacks a corresponding regression test invariant.
2. Whether the per-session verification matrix correctly identifies which sessions are ✓-mandatory vs ▢-soft for invariants 5–9 (DEC-385/386/388/DEF-158/OCA-exempt) AND for the new invariants 19–27.
3. Whether invariant 17 (AMD-2 mechanism-conditional) correctly handles all three H2/H4/H1 branches at S2a — specifically, whether H4 (hybrid) needs nested parametrize for amend-success vs cancel-fallback paths.
4. Whether invariant 20 (pending-reservation state transitions) covers all 5 transitions enumerated in AC3.1 OR whether transition counts could be off (e.g., what about `place_order` returning a non-success status that's neither full-fill nor reject?).
5. Whether invariant 21 (broker-verification three branches) correctly handles the failure-mode case (B-class halt B12) — specifically, whether `verification_failed: true` metadata flag in the alert is operationally meaningful AND whether invariant 25's `verification_stale: true` is the canonical metadata key (it is — invariant 21 references the post-refresh-success branches; invariant 25 is the refresh-failure path).
6. Whether the cumulative-diff soft cap of ~1300 LOC for `order_manager.py` is realistic given the new pending-reservation state machine + Branch 4 coupling + AC2.7 auto-activation + `halt_entry_until_operator_ack` field threading OR needs to be tighter.
7. Whether invariant 19 (`is_reconstructed` refusal) creates a test-coverage hole for operator-manual flatten paths (i.e., does `scripts/ibkr_close_all_positions.py`'s flow get tested?).
8. **(NEW for Round 3 — FAI completeness check per Tier 3 self-falsifiability clause)** Whether the 9-entry FAI in `falsifiable-assumption-inventory.md` and `sprint-spec.md` § Falsifiable Assumption Inventory captures every primitive-semantics assumption load-bearing on the proposed mechanism. If Round 3 finds an additional load-bearing assumption not in the FAI, the inventory has failed and the mechanism's adversarial-review verdict must be downgraded — Decision 7 routes the response (a primitive-semantics-class Critical routes to Phase A re-entry; any other Critical class routes to RSK-and-ship).
9. **(NEW for Round 3 — Cross-Layer Composition Test completeness check per Tier 3 verdict)** Whether the 5 CL tests (CL-1 through CL-5; CL-6 deferred) cover the operationally-relevant compositions OR whether Round 3 surfaces an additional composition that should be covered. (Reviewer note: the CL test count is ABOVE the template's "at least one" floor and ABOVE the Tier 3 verdict's 3-test floor; absent a specific composition the reviewer can identify, the count is sufficient.)
10. **(NEW for Round 3 — Synchronous-update invariant scope check per Tier 3 items A + B)** Whether invariant 23's enumeration of bookkeeping mutation paths (`_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, `_check_sell_ceiling` multi-attribute read) is exhaustive OR whether Round 3 surfaces an additional path that mutates `cumulative_pending_sell_shares` or `cumulative_sold_shares` not in the list.

---

# Embedded: Sprint-Level Escalation Criteria

> Source: `escalation-criteria.md` (Phase C re-sealed, 2026-04-29).

# Sprint 31.92: Sprint-Level Escalation Criteria

> **Phase C artifact 7/9 (revised post-Round-2-Disposition + Phase A
> Re-entry + Phase A Tier 3 + Phase B re-run).** Specific, evaluable
> trigger conditions that halt the sprint and require operator + reviewer
> attention before proceeding. Embedded into every implementation prompt so
> the implementer knows when to halt rather than push through. CRITICAL
> safety sprint — bias toward halt over push-through; the cost of a missed
> halt is a regression of the same mechanism class that empirically
> falsified DEC-386 on 2026-04-28.
>
> **Revision history:** Round 1 authored 2026-04-28 with 14 A-class triggers
> + 11 B-class + 9 C-class. Round-1-revised 2026-04-29: A1/A2 reframed for
> H2-default mechanism choice; new A15 (restart-during-active-position
> regression); new A16 (`is_reconstructed` refusal posture false-positive
> in production); new B12 (broker-verification at suppression timeout
> broken or returns stale data); new C10 (operator-curated hard-to-borrow
> microcap list inadequate); old A11 (ceiling false-positive) expanded to
> cover new pending-reservation race scenarios. Round 2 confirmed all
> Round-1-revised triggers (no net trigger change; 14 dispositions
> distributed across existing triggers). **This Phase C revision (2026-04-29)
> adds the Round 3 Outcome Pre-Commitment (Decision 7 verbatim) as a
> binding subsection AND adds A17 (synchronous-update invariant violation
> per Tier 3 item A), A18 (Branch 4 + H1 active without HALT-ENTRY firing
> per Tier 3 item C), A19 (AC2.7 watchdog auto-activation event per
> Decision 4 — informational, NOT halt) to the A-class trigger table.**
> All Round-1-revised triggers preserved.

---

## Round 3 Operator Override Log Entry

**Audit-trail anchor required by Decision 7's "explicit and logged" clause.**
This subsection reproduces `round-3-disposition.md` § 1 (Operator Override
Invocation) verbatim to provide the in-document audit-trail anchor. The
override is auditable from this artifact directly without requiring
the disposition document.

### 1. Operator Override Invocation (per Decision 7 verbatim)

Decision 7 (verbatim from § Round 3 Outcome Pre-Commitment below)
provides:

> *"Operator override at Round 3 verdict time is permitted but must be
> explicit and logged in the Round 3 disposition."*

**Operator hereby invokes this override.** This subsection logs the
override explicitly per the audit requirement.

### 1.1 What is being overridden

Reviewer recommended Decision 7 (a) routing for C-R3-1 — primitive-
semantics-class Critical → Phase A re-entry per Outcome C. Reviewer's
confidence on FAI-class designation was characterized as
"moderate-to-high" with explicit acknowledgment of the borderline
definitional question of "extension of FAI #2" vs. "new FAI entry."

**Operator overrides to Decision 7 (b) routing** — RSK-and-ship with
in-sprint mitigation, treating C-R3-1 as a known limitation with a
committed in-sprint structural fix (Fix A: single-flight serialization).

### 1.2 Operator's rationale

Three considerations support the override:

**(i) The proposed fix is mechanically simple and well-bounded.** Fix A
(single-flight `asyncio.Lock` + 250ms coalesce window on
`IBKRBroker.refresh_positions()`) is a textbook asyncio concurrency
pattern, ~50 LOC, with a regression test that exercises N concurrent
callers and asserts the race is no longer observable. The fix does NOT
require structural design exploration; it requires implementation +
verification. A full Phase A re-entry's primary value (re-running design
exploration) is low for a fix of this shape.

**(ii) The borderline definitional aspect favors override.** Reviewer
explicitly flagged C-R3-1 as ambiguous-class — "extension of FAI #2" is a
defensible reading. Operator's reading: FAI #2's text covers
*"`ib_async`'s position cache catches up to broker state within
`Broker.refresh_positions(timeout_seconds=5.0)` under all observed
reconnect-window conditions"* — the concurrent-caller surface is a
sibling axis to the reconnect-window axis FAI #2 explicitly covers, not
a structurally-distinct primitive. Treating it as an FAI-#2-extension
(via FAI #10 added at S3b sprint-close) preserves the FAI's structural
defense without invoking the full Phase A re-entry response.

**(iii) Proportionality of response.** Path A (override + in-sprint fix)
costs ~2–3 days from disposition to Phase D start. Path B (Phase A
re-entry + Round 4 full-scope) costs ~5–6 days. The marginal value of
the additional 2–3 days of structured re-review on a settled fix is
bounded; the marginal cost of delayed cessation criterion #5 progress
is real (every day of operator daily-flatten mitigation is operational
risk + operator-process burden).

### 1.3 What the override does NOT do

The override does NOT:
- Dismiss C-R3-1 as a non-finding. C-R3-1 is logged as
  RSK-REFRESH-POSITIONS-CONCURRENT-CALLER at CRITICAL severity (per
  `round-3-disposition.md` § 4).
- Skip the structural fix. Fix A is committed in-sprint at S3b; no
  RSK-and-document-only fallback.
- Skip FAI extension. FAI #10 (concurrent-caller correlation) is
  committed in this disposition; materialized at S3b close-out;
  cross-checked by mid-sprint Tier 3 review (M-R2-5) at S4a-ii close.
  FAI #11 (callsite-enumeration exhaustiveness for H-R3-5) is committed
  in this disposition; materialized at S4a-ii close-out.
- Skip Round 4. The mid-sprint Tier 3 review (M-R2-5) per Round 2
  disposition remains in scope and provides the next structured
  checkpoint after S4a-ii close. M-R2-5 IS the proportional re-review
  for the C-R3-1 fix.

### 1.4 Audit-trail anchors

This override is auditable via:
- The Round 3 disposition document (`round-3-disposition.md` § 1)
- This subsection (in-document audit-trail anchor)
- The Round 3 verdict (`adversarial-review-round-3-findings.md`) which
  documents reviewer's recommended (a) routing — preserves the contrary
  recommendation for retrospective review
- The mid-sprint Tier 3 review verdict (M-R2-5, generated post-S4a-ii)
  which independently checks whether the in-sprint fix successfully
  closes C-R3-1
- Process-evolution lesson F.8 (NEW, captured at sprint-close): "When
  the FAI's self-falsifiability clause fires for a borderline-class
  finding with a mechanically-simple fix, operator override per
  Decision 7 (b) with committed-in-sprint mitigation is a proportional
  response. The pattern is bounded: not every primitive-semantics
  finding warrants the full ceremonial response of Phase A re-entry.
  The mid-sprint Tier 3 review provides the structured re-review at
  proportional cost."

---

## Round 3 Outcome Pre-Commitment (Operator-Bound)

**This subsection is mandatory per the Phase B re-run prompt and the Phase
C generation prompt. It reproduces Decision 7 verbatim. The pre-commitment
is auditable: written before Round 3 runs, not rationalized after the fact.
Operator override at Round 3 verdict time is permitted but must be
explicit and logged in the Round 3 disposition.**

> **Operator pre-commitment for Round 3 outcome (binding):** If Round 3
> produces a Critical finding, the response depends on the finding's class:
>
> (a) **Foundational primitive-semantics miss in the FAI's class** (same
> flavor as the asyncio yield-gap, ib_async cache freshness, and
> callback-path bookkeeping atomicity misses) → another revision pass
> (Phase A re-entry per Outcome C) is required.
>
> (b) **Any other Critical class** (edge case, missing test coverage,
> design refinement, documentation gap, marginal scope concern) → finding
> is accepted as a known limitation, logged as an RSK at appropriate
> severity (MEDIUM-HIGH or higher per Severity Calibration Rubric), and
> sprint ships to implementation.
>
> The pre-commitment is auditable: written before Round 3 runs, not
> rationalized after the fact. Operator override at Round 3 verdict time
> is permitted but must be explicit and logged in the Round 3 disposition.

**Routing notes for Round 3 reviewer:**
- The 9-entry FAI in `falsifiable-assumption-inventory.md` (and reproduced
  verbatim in `sprint-spec.md` § Falsifiable Assumption Inventory) is the
  authoritative list of primitive-semantics assumptions. A Critical that
  surfaces a primitive-semantics assumption *not* in the FAI is the (a)
  class — the FAI's self-falsifiability clause has been triggered for the
  fourth time (Round 1 asyncio yield-gap; Round 2 ib_async cache freshness;
  Phase A Tier 3 callback-path bookkeeping atomicity; Round 3 hypothetical
  fourth).
- A Critical that points to a missing test, a documentation gap, an
  uncovered edge case in an *enumerated* FAI assumption, or an additional
  Cross-Layer Composition Test missing is the (b) class.
- The reviewer is encouraged to flag ambiguous-class findings explicitly
  and let the operator disposition the routing rather than self-routing.

**A14 (Round 2 trigger) carries forward to Round 3:** A14 retains its
Round-2 semantic; if Round 3 fires it (≥1 Critical finding), Decision 7
routes the response per (a) or (b) above.

---

## Trigger Conditions (Halt Conditions)

Each row below specifies a concrete trigger and the required response. If ANY trigger fires, the implementer halts the session, posts to the work-journal conversation, and waits for operator + reviewer disposition before proceeding.

### A. Mandatory Halts (Tier 3 architectural review automatically fires)

| # | Trigger | Required Response |
|---|---------|-------------------|
| A1 | **Spike S1a returns `status: INCONCLUSIVE`** in `scripts/spike-results/spike-def204-round2-path1-results.json` (i.e., findings fall outside H2/H4/H1 from Sprint Spec §"Hypothesis Prescription"). | Halt before S2a impl. Operator arranges Tier 3 review of the alternative mechanism (e.g., a hypothesis the spec author did not enumerate). The S2a/S2b implementation prompts MUST NOT be generated until Tier 3 selects a mechanism. Per protocol §"Hypothesis Prescription": "Do NOT ship a Phase B fix that doesn't address the Phase A finding." |
| A2 | **Spike S1b returns `status: INCONCLUSIVE`** in `scripts/spike-results/spike-def204-round2-path2-results.json` (e.g., locate-rejection error string varies non-deterministically across trials, OR fewer than 5 hard-to-borrow microcap symbols actually got held during paper hours). | Halt before S3a impl. Tier 3 reviews whether to (a) broaden the fingerprint to a regex/list per AC2.1 fallback, (b) accept that the suppression-timeout fallback (AC2.5 broker-verification) is the dominant code path with the 5hr default + AC2.5 broker-verification doing the structural work, OR (c) re-curate the symbol list and re-spike. **Note (Round-1 M-1):** if H6 ruled out (no release events observed), default falls to 18000s with documented rationale per Sprint Spec H6 rules-out condition; this is acceptable for paper-trading initial validation if AC5.5 cessation criterion #5 is the production gate. Tier 3 confirms acceptability. |
| A3 | **Composite validation S5b produces `phantom_shorts_observed > 0`** OR `total_sold_le_total_bought: false` in any synthetic scenario, OR restart-scenario test fails (`is_reconstructed = True` posture allows a SELL through), OR S5c CL-1/CL-2/CL-4/CL-5 fails. | Halt sprint. Do NOT seal. The mechanism closure is empirically falsified; this is the same failure class that ended Sprint 31.91's `~98%` claim. Tier 3 reviews which session's coverage was insufficient and what new mechanism path the validation surfaced. |
| A4 | **Any session's diff modifies a DEC-385/386/388 surface listed in the SbC "Do NOT modify" list** beyond the explicit byte-for-byte preservation OR explicit additive points (POLICY_TABLE entry for sell_ceiling_violation; H2 amend or H1 cancel-and-await consumer at AC1; locate-rejection consumer at AC2.3; broker-verification at AC2.5 + Branch 4; ceiling guard at AC3.2; `is_reconstructed = True` single-line addition inside `reconstruct_from_broker` per AC3.7; `halt_entry_until_operator_ack` field threading per Tier 3 item C). | Halt. RULE-004 + SbC violation. Revert the unintended change. If the change is necessary, escalate — Tier 3 reviews whether the SbC needs amendment OR whether the mechanism itself was wrong. |
| A5 | **DEF-158 retry 3-branch side-check structure is modified** (i.e., a 4th branch is added to `_check_flatten_pending_timeouts` lines ~3424–3489 instead of the spec-prescribed upstream-at-`place_order` detection). | Halt. SbC §"Edge Cases to Reject" #13 violation. The 3-branch side-check (BUY → resubmit / SELL → alert+halt / unknown → halt) is preserved verbatim; Path #2 detection MUST be at the `place_order` exception in the 4 SELL emit sites. Tier 3 reviews whether the design rationale for this separation needs to change. |
| A6 | **Any Tier 2 review on any session produces verdict = CONCERNS or ESCALATE.** | Halt. Operator + Tier 2 reviewer disposition the finding before next session begins. CONCERNS → typically iterate within the same session. ESCALATE → operator decides whether to revert the session's commit or fix forward. |
| A7 | **First post-merge paper session (i.e., the first paper session run AFTER S5c seal) shows ANY new phantom shorts** (vs zero expected for the post-fix state). | Halt sprint. Revert the most recently merged sessions on `main` if specific session(s) can be identified; otherwise revert to pre-S2a HEAD. Tier 3 architectural review of why the validation-layer assertions in S5a + S5b + S5c did not catch the regression. Re-plan the session(s) (likely with new tests added) before re-attempting. **This is the same failure mode that ended DEC-386's `~98%` claim**; the response must be at least as rigorous. |
| A8 | **AC4 ceiling implementation reveals architectural conflict with DEC-369 broker-confirmed reconciliation immunity** — specifically, `reconstruct_from_broker`-derived positions cannot correctly initialize `cumulative_pending_sell_shares = 0`, `cumulative_sold_shares = 0`, `is_reconstructed = True` because the broker query at startup does not preserve fill-history OR the `is_reconstructed` flag interferes with DEC-369's existing reconciliation immunity. | Halt at S4a-i mid-implementation. Tier 3 evaluates whether to (a) treat reconstructed positions as DEC-369-immune AND `is_reconstructed = True` (composing additively — both protections apply), (b) defer ceiling enforcement entirely on broker-confirmed positions until DEF-209 lands (Sprint 35+ Learning Loop V2), or (c) some third option. **Default (a) per Sprint Spec AC3.6 + AC3.7**; option (b) was rejected at Round 1 disposition C-2. SbC §"Adversarial Review Reference" item #5 explicitly flagged this as a scrutiny target; Tier 3 must dispose. |
| A9 | **Path #1 spike S1a measures worst-axis Wilson UB ≥20%** OR observes ≥2 trials where amend semantics non-deterministic. | Halt before S2a (under H2 path). Tier 3 evaluates whether the H2 amend mechanism is unreliable enough that H1 cancel-and-await (last-resort) is the actual default. **HARD GATE per Decision 2:** if `h1_propagation_zero_conflict_in_100 == false` (any 1 conflict in 100 trials), H1 is NOT eligible regardless of `modifyOrder` Wilson UB; surface to operator with explicit "H1 unsafe" determination and require alternative architectural fix (likely Sprint 31.94 D3 or earlier). If S1a's H1 measurement is also ≥500ms p95 OR observes non-convergence: Tier 3 evaluates a deeper architectural question — does ARGUS need to suspend Sprint 31.92 in favor of Sprint 31.94 reconnect-recovery first (which may be the structural cause of the broker latency drift)? |
| A10 | **Path #1 spike S1a OR S2a regression test reveals that the chosen mechanism (H2 amend / H4 hybrid / H1 cancel-and-await) breaks DEC-117 atomic-bracket invariants** (parent-fails-children-cancel pattern OR transmit-flag semantics OR child-OCA-group preservation). | Halt. The do-not-modify boundary on DEC-117 was crossed. Operator decides whether to refine the mechanism approach to preserve DEC-117 OR accept a DEC-117 amendment — the latter requires Tier 3 + adversarial-review re-run. |
| A11 | **AC4 SELL-volume ceiling produces a false-positive in production paper trading post-merge.** Cases: (a) legitimate SELL is refused because `cumulative_pending_sell_shares + cumulative_sold_shares + requested_qty > shares_total` due to fill-callback ordering or partial-fill aggregation defect; (b) `cumulative_pending_sell_shares` not decremented correctly on cancel/reject, causing pending counter to drift upward over session; (c) the C-1 race scenario fires unexpectedly (two coroutines both pass ceiling because reservation didn't hold); (d) **(NEW per Tier 3 items A + B)** a callback-path leak — a bookkeeping mutation path other than `_reserve_pending_or_fail` exhibits an asyncio yield between read and write of the bookkeeping counters, producing a race that invariant 23's AST regression infrastructure should have caught. | Halt. RSK-CEILING-FALSE-POSITIVE materialized. Tier 3 reviews whether to (a) tighten fill-callback aggregation in `on_fill` (adds complexity to a hot path), (b) introduce a small tolerance epsilon (defeats the safety property — REJECTED at spec-time), (c) revert ceiling enforcement until the underlying bug is independently fixed, (d) audit the pending-reservation state transitions per AC3.1 for completeness, OR (e) **(NEW)** audit invariant 23's AST-no-await scan + mocked-await injection regression for false-negative paths. **Default: option (d) — verify which state transition leaks/under-decrements.** Option (e) is the new diagnostic path per Tier 3 items A + B. Option (a) is fallback; option (b) remains REJECTED. |
| A12 | **Any session's diff touches `argus/main.py::check_startup_position_invariant`, `_startup_flatten_disabled`, `argus/main.py:1081` (the `reconstruct_from_broker()` call site), or `argus/execution/order_manager.py::reconstruct_from_broker` BODY beyond the single-line `is_reconstructed = True` addition per AC3.7** (Sprint 31.94 D1+D2 surfaces). | Halt. SbC §"Do NOT modify" violation. These surfaces are time-bounded by Sprint 31.94 per RSK-DEC-386-DOCSTRING. Modification here would couple Sprint 31.92 and 31.94 dependencies and re-introduce the architectural sequencing problem the renumbering resolved. |
| A13 | **Spike artifact `scripts/spike-results/spike-def204-round2-path{1,2}-results.json` is older than 30 days at the time of the FIRST post-merge paper session**, or `ib_async`/IBKR Gateway has been upgraded between spike-run and paper-session. | Halt the post-merge paper session. Operator re-runs both spikes. If both return prior status: proceed with paper session. If S1a or S1b status changes (e.g., locate-rejection string drifted, OR `modifyOrder` Wilson UB shifted, OR `h1_propagation_zero_conflict_in_100` flipped): the closure is invalidated; halt sprint, re-plan affected sessions. (Mirror of DEC-386's `PATH_1_SAFE` 30-day re-validation discipline.) |
| A14 | **Adversarial review Round 3 (Phase C-1, full scope per Outcome C) produces ≥1 Critical finding.** | **Halt prompt generation. Apply Decision 7 routing (binding pre-commitment, see § Round 3 Outcome Pre-Commitment above):** (a) primitive-semantics-class miss → Phase A re-entry per Outcome C; re-author all spec-level artifacts; re-run adversarial review on the post-revision package before proceeding to Phase D. (b) any other Critical class → log as RSK at MEDIUM-HIGH or higher per Severity Calibration Rubric; ship to Phase D. **Round 1 already produced 3 Critical findings; Round 2 produced 1 Critical (A14 fired); Phase A Tier 3 produced 6 DEFs + 2 RSKs. Round 3's bar is the FAI completeness check + cross-layer composition test count + synchronous-update invariant scope.** Operator override at Round 3 verdict time is permitted but must be explicit and logged in the Round 3 disposition. |
| A15 | **(per Round-1 C-2 disposition) Restart-during-active-position regression test (`test_restart_during_active_position_refuses_argus_sells`) fails** at S5b, OR a production paper-session reveals an ARGUS-emitted SELL on an `is_reconstructed = True` position. | Halt sprint. The `is_reconstructed` refusal posture (AC3.7) is the structural defense for the C-2 restart-safety hole; failure means the conservative posture is leaking. Tier 3 reviews whether (a) the field is being correctly set in `reconstruct_from_broker` (single-line addition verified), (b) the ceiling check correctly short-circuits on `is_reconstructed = True` BEFORE any other gate logic, OR (c) DEF-211 D3 (boot-time adoption-vs-flatten policy, Sprint 31.94) needs to be pulled forward. **Note:** this trigger is checking the structural-defense layer; if it fails, DEF-211 D3 must land before live trading. |
| A16 | **(per Round-1 C-2 disposition) The `is_reconstructed = True` refusal posture creates an operationally undesirable failure mode** in production paper trading — i.e., a reconstructed position that needs to be flattened (e.g., for risk-management reasons) cannot be flattened by ARGUS, and operator-manual `scripts/ibkr_close_all_positions.py` is unable to close it for some reason (e.g., script errors, IBKR rejects manual SELL). | Halt sprint. The conservative refusal posture has trapped capital. Tier 3 reviews whether (a) operator-manual flatten infrastructure needs hardening (operational fix), (b) DEF-211 D3 needs to be pulled forward (Sprint 31.94 → Sprint 31.92 partial absorption), or (c) the refusal posture needs immediate amendment to allow specific-flatten-reasons-only (e.g., emergency operator-explicit override). **Default: (a) operational fix first; (c) is risky without DEF-211 D3's policy framework.** |
| A17 | **(NEW per Tier 3 item A — synchronous-update invariant violation)** Synchronous-update invariant violation observed in production paper trading post-merge — i.e., a phantom short OR ceiling false-positive traceable to a callback-path leak (`on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, OR `_check_sell_ceiling` multi-attribute read) that invariant 23's AST-no-await scan + mocked-await injection regression should have caught. | Halt sprint. The invariant 23 regression infrastructure is the structural defense for Tier 3 item A's identified primitive-semantics miss (callback-path bookkeeping atomicity). Tier 3 reviews whether (a) the AST scan has a false-negative path (e.g., a reflective call pattern not covered by Decision 3's three sub-tests), (b) the mocked-await injection test does not cover all entry paths to the bookkeeping mutation, (c) a bookkeeping mutation path was added post-S4a-ii that wasn't covered by the regression. **Default: (a) — extend the AST scan + reflective-pattern coverage to the surfacing path.** This is the same failure-class as DEC-386's empirical falsification: a load-bearing primitive-semantics assumption that the regression infrastructure didn't catch. Decision 7 routes the response if it materializes during Round 3 review (primitive-semantics-class → Phase A re-entry). |
| A18 | **(NEW per Tier 3 item C — Branch 4 + H1 active without HALT-ENTRY firing)** Branch 4 (`verification_stale: true`) fires in production paper trading AND H1 is the active mechanism AND the position is NOT marked `halt_entry_until_operator_ack=True`. The HALT-ENTRY posture failed to engage; FAI #2 + FAI #5 compounded. | Halt sprint. The C-R2-1↔H-R2-2 coupling per Tier 3 item C is the structural defense for the FAI #2 + FAI #5 composite. Tier 3 reviews whether (a) the coupling code path was correctly threaded at S3b, (b) `selected_mechanism` is being correctly read at runtime (e.g., the JSON artifact wasn't re-read after a config reload), (c) `position.halt_entry_until_operator_ack` field is being correctly threaded through ManagedPosition initialization. **Default: (a) — re-verify the S3b implementation against the regression invariant 24 test cases.** S5c CL-3 cross-layer composition is the in-process safety net; if production exhibits this and CL-3 was green, the in-process fixture is missing a path. |
| A19 | **(NEW per Decision 4 — informational, NOT halt)** AC2.7 `_pending_sell_age_seconds` watchdog auto-activates from `auto` to `enabled` in production paper trading. | **Informational logging event, NOT a halt.** Recorded as a structured INFO log line + structured runtime-state event. Operator notification via the existing canonical-logger pipeline. The event signals that the watchdog has detected its first `case_a_in_production` event AND has flipped to `enabled` mode. Sprint-close pre-live transition checklist requires this runtime state to be recorded (per `doc-update-checklist.md` C9). **No sprint-level halt; no Tier 3 review.** Operator may choose to investigate the underlying `case_a_in_production` event (investigation is operational hygiene, not a sprint-gating action). |

### B. Mandatory Halts (Tier 3 not required, but operator + Tier 2 reviewer must disposition)

| # | Trigger | Required Response |
|---|---------|-------------------|
| B1 | **Pre-existing flake count increases.** Specifically: any of DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 fail more frequently than baseline OR a NEW intermittent failure appears that doesn't have a DEF entry yet (RULE-041). | Halt. File DEF entry with symptom + repro hint + xdist worker context. Operator decides whether to fix in this sprint or defer. |
| B2 | **Test count goes DOWN** (regression: existing tests deleted or skipped without explanation). | Halt. RULE-019 violation. Implementer explains in close-out which tests were deleted and why; operator + Tier 2 reviewer assess. |
| B3 | **Pytest baseline ends below 5,269** at the close-out of any session. | Halt. The new tests are additive; existing baseline must hold. Investigate which test broke and either fix or revert. |
| B4 | **CI fails on the session's final commit and the failure is NOT a documented pre-existing flake.** | Halt per RULE-050. Do not proceed to next session until CI green is achieved. RULE-052: if CI is red for a known-cosmetic reason, log that assumption explicitly at each subsequent commit. |
| B5 | **Structural anchor (function name / class name / regex pattern) referenced in impl prompt does not match repo state during pre-flight grep-verify.** | Halt mid-pre-flight. Re-anchor the session's surgical edits against actual current structural anchors. RULE-038 grep-verify discipline. Mark the finding as RESOLVED-VERIFIED if change is already in place, or flag the discrepancy in the close-out. **Note:** absolute line numbers cited in the prompt are "directional only" per protocol v1.2.0+; the structural anchor is what binds. |
| B6 | **A do-not-modify-list file appears in the session's `git diff`.** | Halt. RULE-004 violation. Revert the unintended change before close-out. If the change is necessary, escalate to operator (the do-not-modify list itself needs amendment, OR the spec needs revision). |
| B7 | **Test runtime degrades >2× from baseline** (full suite or scoped) OR a single test's runtime exceeds 60 seconds. | Halt and investigate. Per RULE-037, verify no orphaned background processes are inflating runtime. May be a pyarrow/xdist (DEF-190) recurrence; document in close-out. Path #1 H2 amend OR H1 cancel-and-await fixtures could plausibly add latency to existing trail-flatten tests; benchmark and decide whether to mock the propagation. |
| B8 | **Any session's diff modifies `frontend/`** OR Vitest count changes from baseline 913. | Halt. SbC §"Do NOT modify" #5 violation. Sprint 31.92 has zero frontend scope. Revert. |
| B9 | **Path #2 spike S1b's hold-pending-borrow release window p99 measurement** exceeds the spec-bounded ceiling of 86400s (24hr) — i.e., observed releases take longer than 24 hours from the spike. | Halt at S3a impl. The Pydantic field validator caps at 86400s (24hr); if real-world holds exceed this, the suppression mechanism cannot cover the full window. Operator + Tier 2 disposition: (a) raise the validator ceiling (requires DEC amendment of Config Changes table), OR (b) accept that suppression-timeout broker-verification fallback is the dominant code path within the 24hr window and any longer holds get the existing DEF-158 + DEC-385 reconciliation surface. **Default: (b)** — within bounds for paper trading. |
| B10 | **Any new pytest test exceeds 5s individual runtime** at S5a or S5b or S5c (the validation/cross-layer sessions). | Halt and investigate. Path #1/#2 validation fixtures may have slow synthetic-clock loops or unmocked propagation. The S5c cross-layer composition tests are *expected* to be slower than unit tests (they span multiple modules by design per `templates/sprint-spec.md` v1.2.0) but should still finish in <5s each via `SimulatedBrokerWithRefreshTimeout` fixture mocking; reduce fixture scope OR mock the slow path; do NOT carry slow tests into the final suite. |
| B11 | **Implementer's grep-verify reveals more or fewer occurrences of `_OCA_TYPE_BRACKET` in `argus/execution/order_manager.py` than the 4 specified in S4b's spec** (i.e., line numbers ~3212, ~3601, ~3714, ~3822 + the constant declaration at ~105 — DIRECTIONAL ONLY per protocol v1.2.0+; structural anchors bind). | Halt at S4b. The constant has been used in additional sites since DEC-386 S1b landed; OR the SbC over-counted; OR the file structure has drifted. Re-anchor (search for `_OCA_TYPE_BRACKET` symbolically) and proceed only after operator confirms the actual occurrence count matches the intended replacement scope. |
| B12 | **(per Round-1 H-3 disposition) AC2.5's broker-verification-at-timeout fails or returns stale data** during S3b regression test OR production paper-session. Specifically: `Broker.refresh_positions()` raises an exception, returns timeout, returns stale cache reflecting pre-locate-rejection state, OR the helper logic incorrectly classifies a broker response. | Halt at S3b OR halt sprint if observed post-merge. Operator + Tier 2 disposition: the broker-verification is the structural mitigation for false-positive alerts during reconnect events; if it itself fails, the whole H-3 fix is degraded. **Branch 4 is the structural fallback per Tier 3 item E** — refresh failure publishes alert with `verification_stale: true` metadata (operator-triage signal); HALT-ENTRY coupling under H1 active per Tier 3 item C is the additional safety. Mitigation options: (a) verify Branch 4 + HALT-ENTRY coupling is correctly threaded (regression invariants 24 + 25); (b) accept that Branch 4 catches refresh failure and operator must investigate. **Default: (a) — verify the implementation against regression invariants 24 + 25.** Sprint 31.94 reconnect-recovery may also surface this if `IBKRReconnectedEvent` consumer lands. |

### C. Soft Halts (Continue with extra caution + close-out flag)

| # | Trigger | Required Response |
|---|---------|-------------------|
| C1 | **Implementer notices a bug or improvement opportunity OUTSIDE the current session's scope.** | Document in close-out under "Deferred Items" (RULE-007). Do NOT fix in this session. The maximum-overlap zone (`order_manager.py` touched by 8 of 13 sessions) makes scope discipline load-bearing. |
| C2 | **First fix attempt fails and a second approach emerges.** | Per RULE-008, allow ONE additional approach attempt without operator approval; if that also fails, halt and request guidance. |
| C3 | **Two failed fix attempts on the same bug.** | Switch to diagnostic-first mode (RULE-030). Build a minimal repro outside the application code. Close-out marks Context State YELLOW. |
| C4 | **Context State trending YELLOW** (long conversation, many file reads, many edits). | Per RULE-027, proactively checkpoint: commit, run scoped tests, produce partial close-out, suggest continuing in a fresh session. The 8-of-13-sessions overlap on `order_manager.py` (4,421 lines pre-sprint, growing toward ~5,700 post-sprint per ~1150–1300 LOC cumulative diff bound) means context budget is tight. |
| C5 | **Implementer is uncertain whether a change crosses the do-not-modify boundary** (e.g., a refactor that touches `order_manager.py` near but not in a protected line range; a single-line `is_reconstructed = True` addition that needs to coexist with DEC-369's reconciliation immunity; a `halt_entry_until_operator_ack` field thread that touches `ManagedPosition` initialization). | Pause; consult the SbC do-not-modify list explicitly; if still uncertain, escalate to operator before making the change. Better to halt than to silently regress. |
| C6 | **Phase A's grep-verified line numbers drift 1–5 lines from spec.** | Continue (small drift is RULE-038-acknowledged); document the actual line numbers in the close-out for the next session's reference. Per protocol v1.2.0+, structural anchors bind, not line numbers. |
| C7 | **A test layer's grep regression guard (e.g., S4b's "no `_OCA_TYPE_BRACKET` constant") false-positives on a legitimate site** (e.g., a docstring referencing the prior constant name for historical context). | Add an explicit `# OCA-EXEMPT: <reason>` comment OR use a more specific regex. Document in close-out. Do NOT remove the regression guard. |
| C8 | **S1a/S1b spike output JSON schema does not exactly match the schema specified in the spec** (e.g., field names differ slightly because the operator-developer revised them during the spike). | Continue. Document the actual schema in the close-out. The downstream impl prompts at S2a/S2b/S3a/S3b consume the JSON; minor schema deviations are acceptable as long as the gating fields (`status`, `selected_mechanism`, `recommended_locate_suppression_seconds`, exact fingerprint string, `worst_axis_wilson_ub`, `h1_propagation_zero_conflict_in_100`) are present and meaningful. |
| C9 | **AC3.4 "per-managed-position ceiling" test (deferred to S5b) reveals that two ManagedPositions on same symbol DO interact in some unexpected way** (e.g., one position's `cumulative_pending_sell_shares` increment fires on the wrong fill due to order-id collision). | Halt the AC3.4 test, investigate. If the interaction is a pre-existing OrderManager bug surfaced by the new field, file a DEF and decide scope (fix in S5b or defer). If the interaction is introduced by AC3.1 increment logic, fix at S5b OR escalate to S4a-i hotfix. |
| C10 | **(per Round-1 M-1 disposition) Operator-curated hard-to-borrow microcap list at S1b includes < 5 symbols, OR none of the curated symbols actually trigger locate-rejection during paper-IBKR spike trials.** | Continue with documented caveat. If <5 symbols: operator notes the list size in spike close-out + spike result JSON. If no rejections triggered: H6 RULES-OUT condition fires per Sprint Spec; default falls to 18000s with documented rationale per Sprint Spec H6 rules-out path; AC2.5 broker-verification fallback receives extra emphasis in S5b validation; AC2.7 watchdog auto-activation per Decision 4 catches any unmodeled locate-rejection string variant in production. **NOT a halt** — the design tolerates this case via H6's documented rules-out branch. |
| C11 | **(per Round-1 H-4 disposition) Implementer's startup CRITICAL warning at S4b emits to a log destination that operator wouldn't notice** (e.g., a file-only log handler without console mirroring). | Verify at S4b that the dual-channel emission per H-R2-4 / AC4.6 is fully wired: ntfy.sh `system_warning` urgent AND canonical-logger CRITICAL with phrase "DEC-386 ROLLBACK ACTIVE." Both emissions captured at startup; tested via log-capture fixture. If either channel is silently filtered: investigate the log-handler config; ensure CRITICAL-level emissions are not suppressed in any production-config path; ensure ntfy.sh topic `argus_system_warnings` is correctly wired. Document log-destination in close-out. |
| C12 | **(NEW per H-R2-4 — `--allow-rollback` flag verification)** S4b regression test for `--allow-rollback` flag absent path (`bracket_oca_type != 1` AND flag absent → exit code 2 + stderr FATAL banner) is missing OR fails due to test fixture issues. | Continue with extra scrutiny. AC4.7 has two paths: (a) `--allow-rollback` flag present + `bracket_oca_type != 1` → AC4.6 dual-channel emission fires + ARGUS proceeds to start; (b) `--allow-rollback` flag absent + `bracket_oca_type != 1` → exit code 2 + stderr FATAL banner ("DEC-386 ROLLBACK REQUESTED WITHOUT --allow-rollback FLAG. Refusing to start."). Both paths need explicit regression tests in `tests/execution/order_manager/test_def212_oca_type_wiring.py`. Document any test infrastructure issue in close-out. |

## Escalation Targets

For each halt, the escalation flows as follows:

- **Code-level questions** (does this approach work?): Tier 2 reviewer (the `@reviewer` subagent in the same session) is first-line; operator is second-line.
- **Spec-level questions** (does this still match the Sprint Spec?): Operator + sprint-planning conversation are required.
- **Architectural questions** (does this change a DEC?): Tier 3 reviewer in a separate Claude.ai conversation, with operator dispositioning the verdict.
- **Safety questions** (does this risk paper-trading regressions or live trading consideration?): Operator + Tier 3 reviewer; pause paper trading if in doubt.
- **Round 3 verdict-class questions** (Critical class disposition under Decision 7): Operator override is permitted but must be explicit; logged in the Round 3 disposition. The pre-commitment is the default; override is the exception.

## Sprint Abort Conditions

The sprint as a whole is aborted (not just an individual session) if ANY of:

1. **Three or more A-class halts within the same week.** Indicates the spec or the underlying mechanism understanding is wrong; the sprint needs replanning. Sprint 31.91 had two Tier 3 reviews + two in-sprint hotfixes; that pattern is sprint-stretch-but-acceptable. **Three or more A-class halts** crosses into replanning territory.

2. **Mechanism turns out to be different from S1a/S1b spike findings** (DEBUNKED status). E.g., a paper session shows phantom shorts traceable to a third path (Path #3) not enumerated by Phase A. RULE-051 (mechanism-signature-vs-symptom-aggregate) — investigate whether the spike's characterization was incomplete OR whether the Apr 28 debrief itself missed a third mechanism. Pivot to a Sprint 31.92.5 or 31.93-prefix sprint with new diagnostic before continuing.

3. **Three failed paper sessions post-S5c seal** — i.e., DEF-204 mechanism keeps firing despite the architectural closure landed. Would mean DEC-390 itself was wrong, similar to DEC-386's empirical falsification on 2026-04-28. The decision-log entry would be marked SUPERSEDED-BY-NEXT-DEC, and a new diagnostic phase opens. **This abort condition's existence is itself evidence-based design** — we have learned from Sprint 31.91 that architectural closures need empirical falsification, not just test-suite green.

4. **Phase 0 housekeeping invalidated** — i.e., a parallel sprint or impromptu has renumbered or renamed Sprint 31.93/31.94/31.95 in a way that conflicts with Sprint 31.92's cross-references in DEF-208/211/212/215 routing columns. Halt; reconcile cross-references; re-issue Phase 0 patch before resuming Phase D. (Low likelihood; flagged for completeness.)

5. **Live trading enabled mid-sprint** by operator decision (without sprint completion). **Sprint Spec §"Out of Scope" item 16** explicitly defers live-trading enablement; sprint must complete in paper before any live transition consideration. If operator decides to transition early regardless, sprint is paused (not aborted) until the transition is reverted OR sprint is rebaselined for the new context.

6. **DEC-390 cannot be coherently materialized at sprint-close** — e.g., the four layers (Path #1 + Path #2 + ceiling + DEF-212 rider) end up addressing different mechanisms than spec-anticipated, OR adversarial review reveals an architectural conflict between L1 and L3 that requires splitting DEC-390 into multiple DECs. **Default disposition: split the DEC and proceed with sprint-close** — this is not a sprint-abort trigger but a doc-sync complication. Listed here for completeness.

7. **(per Round-1 C-2 disposition + H-R2-3 escalation per Phase B Severity Calibration Rubric) The `is_reconstructed = True` refusal posture creates a sustained operational degradation across multiple paper sessions** — i.e., reconstructed positions accumulate AND operator daily-flatten cannot keep up AND DEF-211 D3 is more than **2 weeks** away (was 4 weeks pre-Phase-B; lowered per H-R2-3 + Severity Calibration Rubric MEDIUM-HIGH floor — operator daily-flatten empirically failed Apr 28 with 27 of 87 ORPHAN-SHORT detections from a missed run). Sprint is paused (not aborted); Sprint 31.94 D3 pulled forward as priority OR operator daily-flatten infrastructure receives emergency hardening. Sprint 31.92's structural fix is correct; the operational consequence may require schedule adjustment.

8. **(NEW per Tier 3 verdict — FAI self-falsifiability triggered fourth time)** Round 3 produces a primitive-semantics-class Critical AND Decision 7 routes to (a) Phase A re-entry. The fourth FAI miss within a single sprint's planning cycle (Round 1 asyncio yield-gap; Round 2 ib_async cache freshness; Phase A Tier 3 callback-path bookkeeping atomicity; Round 3 hypothetical fourth) is a structural signal that the mechanism understanding is incomplete in a way the FAI infrastructure itself cannot bound. **Default disposition: Phase A re-entry per Outcome C, NOT sprint abort.** Listed as a sprint abort consideration only for completeness — the design intent is that Decision 7 (a) routes to revision, not abort. Operator may choose to escalate to abort only if Round 3 surfaces evidence that the mechanism architecture itself (not just FAI completeness) is wrong.

9. **(NEW per Round 3 C-R3-1 — Fix A serialization spike failure.)** If Fix A serialization spike (S3b sub-spike for FAI #10) fails AND no alternative serialization design surfaces, sprint halts; operator decides whether to escalate to Phase A re-entry retroactively. This abort condition is the binding contract on the C-R3-1 operator-override (per § 1 Operator Override Invocation above) — the in-sprint mitigation Path is conditional on Fix A's empirical falsifiability holding. If S3b's N=20 concurrent-caller spike returns the race observable WITH the mitigation enabled (i.e., the lock + coalesce-window pattern fails to serialize), the override is empirically retracted and Phase A re-entry retroactively reactivates. Operator decision required to escalate; default disposition is sprint halt + Phase A re-entry.

## Closing the Sprint

The sprint may be sealed (D14 sprint-close doc-sync) only when ALL of:

- All 13 sessions have Tier 2 verdict CLEAR (or CONCERNS dispositioned to CLEAR via re-iteration).
- Mid-Sprint Tier 3 Review (M-R2-5, between S4a-ii and S4b/S5a/S5b/S5c) verdict received (PROCEED / REVISE_PLAN / PAUSE_AND_INVESTIGATE) and dispositioned. PROCEED → continue. REVISE_PLAN → re-plan affected sessions before continuing. PAUSE_AND_INVESTIGATE → halt sprint.
- S5a's `sprint-31.92-validation-path1.json` artifact committed to `main` with `path1_safe: true`.
- S5b's `sprint-31.92-validation-path2.json` artifact committed to `main` with `path2_suppression_works: true` AND `broker_verification_at_timeout_works: true`.
- S5b's composite Pytest test (`test_composite_validation_zero_phantom_shorts_under_load`) green AND artifact `sprint-31.92-validation-composite.json` committed to `main`.
- S5b's restart-scenario test (`test_restart_during_active_position_refuses_argus_sells`) green.
- **S5c's 5 cross-layer composition tests (CL-1 through CL-5) green** AND `tests/integration/conftest_refresh_timeout.py` (`SimulatedBrokerWithRefreshTimeout` fixture) committed AND the dedicated Branch 4 unit test green.
- Full suite green at S5c close-out (DEC-328 final-review tier; full suite mandatory).
- DEC-390 written below in `docs/decision-log.md` with all 4 layers and complete cross-references AND structural-closure framing (NOT aggregate percentage claims) per AC6.3.
- DEF-204 row in `CLAUDE.md` marked **RESOLVED-PENDING-PAPER-VALIDATION** (NOT RESOLVED — per SbC §"Edge Cases to Reject" #14).
- DEF-212 row in `CLAUDE.md` marked **RESOLVED**.
- 6 NEW DEFs from Tier 3 added to `CLAUDE.md` DEF table: DEF-FAI-CALLBACK-ATOMICITY, DEF-CROSS-LAYER-EXPANSION, DEF-FAI-N-INCREASE, DEF-FAI-2-SCOPE, DEF-FAI-8-OPTION-A, DEF-SIM-BROKER-TIMEOUT-FIXTURE.
- `docs/dec-index.md` updated with DEC-390 entry.
- `docs/sprint-history.md` row added.
- `docs/roadmap.md` updated per `doc-update-checklist.md`.
- Cessation criterion #5 counter explicitly RESET to 0/5 for the new post-Sprint-31.92 paper-session window. (Sprint 31.91's prior #5 counter is supersumed.)
- Daily CI workflow added for composite test freshness (per AC5.3 + Round-1 M-3 disposition).
- 7 new RSKs filed: RSK-DEC-390-AMEND (if H2) OR RSK-DEC-390-CANCEL-AWAIT-LATENCY (if H1/H4 with H1 fallback path active), RSK-DEC-390-FINGERPRINT, RSK-CEILING-FALSE-POSITIVE, RSK-RECONSTRUCTED-POSITION-DEGRADATION (severity MEDIUM-HIGH; time-bounded by Sprint 31.94 D3), RSK-SUPPRESSION-LEAK, RSK-FAI-COMPLETENESS (Tier 3-class), RSK-CROSS-LAYER-INCOMPLETENESS (Tier 3-class).
- Process-evolution lesson F.5 reaffirmation captured in `docs/process-evolution.md` (per `doc-update-checklist.md` C10) AND FAI completeness pattern lesson AND CL-6 deferral rationale.
- Pre-live transition checklist updated with Sprint 31.92 gates AND `pending_sell_age_watchdog_enabled` runtime state recording AND `--allow-rollback` flag verification (absent in production startup config).

---

*End Sprint 31.92 review-context.md.*
