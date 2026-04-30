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

27. **Worst-axis Wilson UB across all four adversarial axes as the
    binding metric for Path #1 mechanism selection.** Per Tier 3 Review
    #2 verdict 2026-04-30 / DEC-390 amended rule: superseded by axis
    (i) production-reachable steady-state as the sole binding axis
    (`axis_i_wilson_ub`); axes (ii) reconnect-window and (iv) joint
    reconnect+concurrent are RETAINED in the spike harness as
    informational characterization of H2 fail-loud behavior during
    Gateway disconnect (input to Sprint 31.94 reconnect-recovery
    design per DEF-241 / RSK-DEC390-31.94-COUPLING); axis (iii)
    stale-ID is DELETED entirely (state unreachable in production per
    DEC-117 + DEC-386 invariants; broker-correct rejection of
    modifications against cancelled orders is *desired* behavior, not
    a rejection-rate signal — including a desired-behavior signal in
    the binding metric is structurally degenerate). The strict reading
    of FAI #3 ("ALL four axes must remain ≤5% UB") would have
    structurally disqualified H2, H4, AND H1 simultaneously by design
    (axis (iii) at 100% UB), which is not a useful selection criterion.
    The loose reading recovers the engineering question: "does H2 work
    in steady-state production load, and does it fail loud — not silent
    — during the separately-addressed reconnect failure mode?"
    **Status update (Tier 3 Review #3 2026-04-30):** STRUCTURALLY MOOT.
    Item 27's framing presumes the H2/H4/H1 threshold-tiered selection
    rule, which Tier 3 #3 replaced with the Mechanism A binary gate
    (item 28 below). The axis-binding distinction is preserved here
    only as historical narrative for the prior selection rule. The
    spike v2 attempt 1 JSON artifact's `informational_axes_results`
    (axes (ii)/(iv)) remain available to Sprint 31.94 grounding per
    DEF-241; that cross-sprint coupling is unaffected by item 28.
    Cross-references: DEC-390 (Pattern B sprint-close materialization;
    Tier 3 #3 amends DEC-390's narrative to describe Mechanism A's
    binary gate); sprint-spec.md §Hypothesis Prescription amended
    halt-or-proceed gate language; FAI #3 (this file's §Edge Case 2
    + companion `falsifiable-assumption-inventory.md` entry #3 —
    both amended at this Tier 3 #3 mid-sync);
    RSK-VERDICT-VS-FAI-3-COMPATIBILITY (`docs/risk-register.md` —
    CLOSED-SUPERSEDED at Tier 3 #3).

28. **Mechanism B (cancel-bracket / submit-fresh-bracket) and Mechanism
    C (OCA-membership manipulation) — eliminated per Tier 3 Review #3
    verdict; future architectural reconsideration only if Mechanism A's
    Mode-D-equivalent gate fails.** Per Tier 3 Review #3 verdict
    2026-04-30 / Question 2 Answer / Candidates evaluated table:
    Mechanism B has strictly larger surface area than Mechanism A for
    the same outcome (larger unprotected window: must wait for cancel
    propagation AND new bracket placement; stronger interaction with
    DEC-385 mid-flight reconciliation; no advantage). Mechanism C is
    empirically uncharacterized but most likely eliminated by the same
    broker-policy class that blocks `modify_order` against auxPrice
    (OCA membership is overwhelmingly likely to be immutable
    post-creation under the same enforcement regime); even if it
    works, the "removed-from-OCA" window introduces a NEW unprotected
    window during which a concurrent fill of an OCA sibling can fire
    without atomic cancellation. Both are STRICTLY WORSE than
    Mechanism A and are out of scope for Sprint 31.92. Future
    architectural reconsideration is gated on Mechanism A's Unit 6
    Mode-D-equivalent gate failing (escalation-criteria.md A20). In
    that case, Tier 3 Review #4 would relitigate the architectural
    space; until then, Mechanism A is the sole viable mechanism.
    Cross-references: DEF-242 (architectural finding driving the
    elimination of H2/H4); DEF-245 (Unit 6 follow-on spike scope);
    RSK-MECHANISM-A-UNPROTECTED-WINDOW (`docs/risk-register.md` —
    gate-coupling; revisit at Unit 6 close-out);
    `tier-3-review-3-verdict.md` §Question 2 Answer.

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

2. **IBKR returning a `modifyOrder` rejection during Path #1 for
   reasons other than "stop price invalid" (e.g., 201 margin rejection,
   transmit-flag conflict).** **AMENDED (Tier 3 Review #3 2026-04-30):**
   Out of scope, AND structurally moot because Path #1's mechanism
   is now Mechanism A (cancel-and-resubmit-fresh-stop) — H2 (modify_order
   PRIMARY DEFAULT) and H4 (hybrid amend) were ELIMINATED-EMPIRICALLY
   when IBKR's broker policy was confirmed to categorically reject
   `modify_order` against any OCA group member (Error 10326; DEF-242).
   Mechanism A does not call `modify_order`, so unusual amend rejections
   cannot fire on the Path #1 hot path. Cross-references: DEF-242
   (architectural finding); §"Out of Scope" item 28 (Mechanism B + C
   eliminated); `tier-3-review-3-verdict.md` §Question 1 Answer.

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

17. **Aggregate percentage closure claims in DEC-391.** Per
    process-evolution lesson F.5 (captured at sprint-close per
    `doc-update-checklist.md` C10): DEC entries claiming closure should
    use "structural closure of mechanism X with falsifiable test fixture
    Y" rather than "closes ~Z% of blast radius." DEC-386's `~98%` claim
    was empirically falsified 24 hours later; DEC-391 must NOT repeat
    the pattern. AC6.3 mandates structural framing. **Edge case to
    reject:** any draft DEC-391 text using "comprehensive," "complete,"
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
  preserve (per Phase A leave-as-historical decision). DEC-391 is a new
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
| Locate-rejection error-string drift quarterly re-validation | Operational hygiene, post-Sprint-31.92-merge | RSK-DEC-391-FINGERPRINT (proposed at sprint-close) |
| Path #1 H2 amend-stop-price IBKR-API-version assumption documentation | `docs/live-operations.md` paragraph at sprint-close | RSK-DEC-391-AMEND (proposed at sprint-close) |
| Path #1 H1 cancel-and-await unprotected-window documentation | `docs/live-operations.md` paragraph at sprint-close (only if H1 selected) | RSK-DEC-391-CANCEL-AWAIT-LATENCY (proposed at sprint-close, conditional on H1 selection) |
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
