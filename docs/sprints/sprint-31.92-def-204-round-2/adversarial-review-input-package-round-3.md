# Sprint 31.92 — Adversarial Review Input Package — Round 3

> **Phase C artifact 9 of 9 — final Phase C deliverable for Sprint 31.92.**
> Authored 2026-04-29 (ET). This artifact is the BINDING input to the Round 3
> adversarial reviewer. Reviewer reads this single file (plus the revised
> `sprint-spec.md` and `spec-by-contradiction.md` referenced inline as the
> authoritative spec documents) and produces a verdict per
> `protocols/adversarial-review.md` v1.1.0 § Resolution.
>
> **Outcome C declaration (verbatim):** Round 3 scope is FULL per
> `protocols/adversarial-review.md` v1.1.0 § Outcome C. Round 2 disposition's
> narrowest-possible-scope recommendation is SUPERSEDED.
>
> **Binding protocol versions (declared at Phase B re-run + Phase C
> authoring time, 2026-04-29):**
> - `protocols/adversarial-review.md` v1.1.0
> - `protocols/sprint-planning.md` v1.3.0
> - `protocols/tier-3-review.md` v1.1.0
> - `templates/sprint-spec.md` v1.2.0
> - `templates/spec-by-contradiction.md` v1.1.0
>
> **Disposition routing (binding pre-commitment):** Decision 7 — operator
> pre-commitment for Round 3 outcome — bounds Round 3 verdict routing.
> Reproduced verbatim in § 2 below. Reviewer must read Decision 7 before
> producing a Critical-class finding so the routing implications are
> understood at verdict-authoring time, not after.

---

## Phase C consistency note for the operator

`docs/architecture.md` was NOT uploaded with the Phase C artifact set
(uploads listed: `design-summary.md`, `sprint-spec.md`,
`spec-by-contradiction.md`, `falsifiable-assumption-inventory.md`,
`phase-a-reentry-findings.md`, `session-breakdown.md`,
`regression-checklist.md`, `escalation-criteria.md`,
`doc-update-checklist.md`, `round-2-disposition.md`, `revision-rationale.md`,
`tier-3-review-1-verdict.md`). The Round 3 input package's § 7
(Architecture document excerpts) consequently quotes the **Sprint Spec's
Deliverables 1–4 + Acceptance Criteria** as the authoritative description
of the architectural surfaces this sprint modifies — the spec describes
exactly which `Broker` ABC additions, which `OrderManager` field/method
additions, which `POLICY_TABLE` extensions are in scope. Round 3 reviewer
should read the actual `docs/architecture.md` §3.3 / §3.7 / §13 from the
repo at `https://github.com/stevengizzi/argus.git` HEAD (Sprint 31.91
sealed 2026-04-28; Sprint 31.92 has not landed yet) to ground the design
review in current code surfaces. The spec's descriptions are the
authoritative description of CHANGES; the architecture.md content at HEAD
is the authoritative description of PRE-CHANGE state.

This is surfaced as a Phase C consistency finding per the Phase C
generation prompt's "If you find a contradiction between artifacts 1–8
and the Round 3 input package you're authoring, surface it as a Phase C
consistency finding to the operator — do not silently reconcile."
**Operator may choose to:** (a) upload `docs/architecture.md` and have the
package re-authored with verbatim §3.3/§3.7/§13 quotes; (b) accept the
current package's spec-as-architectural-anchor framing; (c) request that
the Round 3 reviewer read architecture.md from the repo as part of their
package digest. The package below is structured for option (b)/(c)
without prejudice.

---

## 1. Round 3 Framing

### Round 3 declaration

This is **Round 3** of adversarial review for Sprint 31.92. Round 1
produced 3 Critical + 4 High + 3 Medium findings (Outcome B). Round 2
produced 1 Critical + 5 High + 5 Medium + 3 Low findings; A14 fired
(Round 2 produced ≥1 Critical). Phase A re-entry was triggered per
`protocols/adversarial-review.md` v1.1.0 § Outcome C ("same primitive-
semantics assumption *class* caught in two consecutive rounds"). Phase A
Tier 3 review #1 (2026-04-29) produced REVISE_PLAN. Phase B re-run +
Phase C re-revision (2026-04-29) materialized 7 settled operator
decisions + 5 Tier 3 mandated revisions A–E. Round 3 runs on the
post-revision Phase C package.

### Reviewer's binding context

Round 3 is a **fresh independent design review at full scope**, not a
delta-only review against Round 2. The reviewer applies all probing-sequence
steps from `protocols/adversarial-review.md` v1.1.0 §"Probing Sequence":

1. Assumption Mining (with mandatory Falsifiable Assumption Inventory
   cross-check)
2. Failure Mode Analysis
3. Future Regret
4. Specification Gaps
5. Integration Stress
6. Simulated Attack (if security-relevant)

The Round 2 disposition's recommendation of "narrowest possible scope"
(line 454 of `round-2-disposition.md`, dated 2026-04-29) is **SUPERSEDED**
by the 2026-04-29 amendment to `protocols/adversarial-review.md` v1.1.0 §
Outcome C, which mandates that Round (N+2) after Outcome C re-fire is
"full scope, not narrowed." Reviewer applies full scope.

### Decision 7 — operator pre-commitment for Round 3 outcome (verbatim from `escalation-criteria.md` § Round 3 Outcome Pre-Commitment)

**This subsection is mandatory per the Phase B re-run prompt and the Phase
C generation prompt. It reproduces Decision 7 verbatim. The pre-commitment
is auditable: written before Round 3 runs, not rationalized after the
fact. Operator override at Round 3 verdict time is permitted but must be
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

**Routing notes for Round 3 reviewer (verbatim from `escalation-criteria.md`):**

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

## 2. Sprint Context

### Sprint 31.91 sealed 2026-04-28

DEC-385 (Side-Aware Reconciliation Contract — 6 layers), DEC-386
(OCA-Group Threading + Broker-Only Safety — 4 layers), and DEC-388 (Alert
Observability Architecture — multi-emitter consumer pattern with
HealthMonitor as central consumer; 5 layers) materialized at sprint-close.
22 shadow variants are collecting CounterfactualTracker data. 5,269 pytest
+ 913 Vitest at HEAD.

### DEC-386 empirical falsification 2026-04-28

DEC-386's `~98%` aggregate-coverage claim was empirically falsified the
same day Sprint 31.91 sealed. The 2026-04-28 paper-session debrief
(`docs/debriefs/2026-04-28-paper-session-debrief.md`) recorded **60 NEW
phantom shorts** via two uncovered mechanism paths the DEC-386 closure
did not anticipate:

- **Path #1 — trail-stop / bracket-stop concurrent-trigger over-flatten
  on BITU.** Trail flatten and emergency flatten both emit standalone
  SELL orders against the same `ManagedPosition` between the trail-stop
  decision and the emergency-flatten decision; the resulting
  `total_sold > shares_total` flips the position short.
- **Path #2 — locate-rejection-as-held retry storm on PCT.** IBKR
  rejected the SELL order with locate-rejection on a hard-to-borrow
  microcap; ARGUS retried at the next tick; broker held the rejected
  order pending borrow (case A, NOT exception case B) AND filled it
  on borrow availability concurrent with the retry-emitted SELL,
  flipping the position short.

The 60 NEW phantom shorts are independent of the 11 phantom shorts DEC-386
recovered before sealing. Sprint 31.92 is the response sprint. Operator
runs `scripts/ibkr_close_all_positions.py` daily until cessation criterion
#5 (5 paper sessions clean post-Sprint-31.92 seal) is satisfied.

### Sprint 31.92 — DEF-204 Round 2

Sprint 31.92 closes DEF-204's two empirically-falsifying mechanism paths
via spike-driven mechanism selection (H2 amend-stop-price PRIMARY DEFAULT
/ H4 hybrid fallback / H1 cancel-and-await LAST-RESORT) plus structural
defense-in-depth at four layers (L1 mechanism / L2 fingerprint +
position-keyed suppression + broker-verified timeout / L3 long-only
SELL-volume ceiling with concurrency-safe pending-share reservation +
reconstructed-position refusal posture / L4 DEF-212 `_OCA_TYPE_BRACKET`
constant drift fix with operator-visible rollback warning + `--allow-rollback`
CLI gate). DEC-390 materializes at sprint-close with structural-closure
framing (NOT aggregate percentage claims, per process-evolution lesson
F.5).

### 2026-04-29 protocol amendments installed

Three protocol amendments landed concurrently 2026-04-29, driven by the
Sprint 31.92 Round 1 + Round 2 + Phase A Tier 3 pattern:

- **`templates/sprint-spec.md` v1.2.0 § Falsifiable Assumption Inventory**
  — new mandatory section for sprints touching safety-load-bearing code.
  Self-falsifiability clause is load-bearing: "If a future adversarial
  review finds an additional primitive-semantics assumption load-bearing
  on the mechanism not in this list, the inventory has failed — and the
  mechanism's adversarial-review verdict must be downgraded accordingly."
- **`protocols/tier-3-review.md` v1.1.0 trigger #5** — new trigger:
  "Adversarial review N≥2 with Critical-of-FAI-class in two consecutive
  rounds." Independently fires Phase A Tier 3 review.
- **`protocols/adversarial-review.md` v1.1.0 § Outcome C** — three-state
  outcome machine (A: Round CLEAR / B: Round produced revisions /
  C: Pattern of repeated Criticals → return to Phase A). Outcome C
  requires Round (N+2) full-scope.

These amendments are operating constraints for Round 3.

### Three FAI-class primitive-semantics misses to date

| # | Round | Date | Missing primitive | Surfaced by |
|---|-------|------|-------------------|-------------|
| 1 | Round 1 | 2026-04-28 | asyncio yield-gap (coroutines yielding control during `await`; concurrent emit-time bookkeeping not serialized) | Round 1 reviewer; C-1 finding |
| 2 | Round 2 | 2026-04-29 | `ib_async` position-cache freshness (`broker.get_positions()` is local-cache lookup; stale during reconnect window) | Round 2 reviewer; C-R2-1 finding |
| 3 | Phase A Tier 3 | 2026-04-29 | callback-path bookkeeping atomicity (asyncio guarantee applies to ALL paths mutating bookkeeping counters, not only `_reserve_pending_or_fail`) | Tier 3 reviewer; FAI item A finding |

Process-evolution lesson F.6 captures the pattern: "primitive-semantics
assumptions whose violation silently produces the symptom class the
proposed fix claimed to address." Round 3 full-scope cross-check is the
next defense layer per the FAI's self-falsifiability clause.

---

## 3. Review History

### Round 1 (2026-04-28) verdict summary

**Outcome:** B (Round produced revisions).

**Findings:** 3 Critical + 4 High + 3 Medium.

**Critical findings:**

- **C-1 — `cumulative_sold_shares` reads stale data between emit and fill.**
  Reviewer's argument: two coroutines on the same `ManagedPosition` can
  both pass `_check_sell_ceiling` between `t=emit` and `t=fill` because
  asyncio yields control during `await place_order(...)`. The ceiling reads
  stale state. SbC §"Edge Cases to Reject" #1 conflated fill-side
  serialization (which asyncio provides) with emit-side serialization
  (which it does not). Disposition: **ACCEPT**. Fix: two-variable
  accounting — `cumulative_pending_sell_shares` (incremented at place-time,
  synchronously before the `await`) plus `cumulative_sold_shares`
  (incremented at fill-time). **This is the asyncio yield-gap primitive-
  semantics miss — the first FAI-class finding.**
- **C-2 — Restart-safety hole degrades both Path #1 and ceiling.** On
  `reconstruct_from_broker`-derived positions, the ceiling forgets prior
  sells (`cumulative_sold_shares = 0`) and Path #1's cancel-and-await
  catches only non-OCA orders, leaving pre-restart bracket children alive
  at IBKR. Disposition: **PARTIAL ACCEPT (different)**. Fix:
  `is_reconstructed: bool = False` flag set True in
  `reconstruct_from_broker`; ceiling refuses ALL ARGUS-emitted SELLs on
  reconstructed positions until Sprint 31.94 D3 lands.
- **C-3 — H1 cancel-and-await default reintroduces AMD-2's closed gap.**
  AMD-2 ("sell before cancel") was introduced in Sprint 28.5 specifically
  because cancel-then-sell leaves an unprotected window during cancel
  propagation. H1 reintroduces exactly that window. H2 (amend-stop-price)
  is structurally safer. Disposition: **ACCEPT**. Fix: reverse
  Hypothesis Prescription — H2 PRIMARY DEFAULT / H4 fallback / H1
  LAST-RESORT.

**High findings:** H-1 (ceiling-applicability ambiguity at bracket
placement); H-2 (suppression dict keyed by symbol vs. position);
H-3 (broker-side verification at suppression-timeout); H-4 (DEF-212 rider
config defaults).

**Medium findings:** M-1 (suppression default derived from S1b spike, not
hardcoded 5min); M-2 (AC5.1/AC5.2 reframed as in-process logic
validation); M-3 (Pytest with JSON side-effect for composite validation).

**Disposition outcome:** All 10 findings dispositioned in
`revision-rationale.md` (Round 1); 7 ACCEPT in full, 3 PARTIAL ACCEPT
with different fix shape. Round 2 required (substantive revisions).

### Round 2 (2026-04-29) verdict summary

**Outcome:** B (Round produced revisions). **A14 fired** — Round 2
produced ≥1 Critical of the FAI's primitive-semantics class.

**Findings:** 1 Critical + 5 High + 5 Medium + 3 Low.

**Critical finding:**

- **C-R2-1 — H-3 broker-verification depends on unverified `ib_async`
  cache-freshness behavior.** The Round 1 disposition's chosen H-3 fix
  (broker-verification at suppression timeout via `broker.get_positions()`)
  inherits the cache-staleness problem the reconnect-event-consumer
  alternative was designed to eliminate. `ib_async` maintains a local
  position cache populated by `positionEvent` subscriptions;
  `IB.positions()` is a synchronous local-cache lookup, NOT a broker
  round-trip. After a reconnect, during the reconnection-and-resubscription
  window, the cache returns the pre-disconnect state. AC2.5's three-branch
  logic classifies stale-cached-long as Branch 1 (silent INFO; clear dict
  entry), masking exactly the post-reconnect anomaly the verification was
  designed to catch. Disposition: **PARTIAL ACCEPT (different)**. Fix:
  new `Broker.refresh_positions()` ABC method; AC2.5 forces refresh-then-verify;
  new Branch 4 ("reconnect-stale") fires alert with `verification_stale: true`.
  **This is the `ib_async` cache-freshness primitive-semantics miss — the
  second FAI-class finding.**

**High findings:** H-R2-1 (atomic `_reserve_pending_or_fail()` with
AST-level guard); H-R2-2 (HALT-ENTRY under H1 + locate-rejection;
S1a halt-or-proceed gate tightened); H-R2-3 (RSK-RECONSTRUCTED-POSITION-DEGRADATION
re-rated MEDIUM-HIGH; Sprint Abort Condition #7 lowered to 2 weeks);
H-R2-4 (combined: AC4.6 dual-channel CRITICAL warning + AC4.7
`--allow-rollback` CLI gate); H-R2-5 (`is_stop_replacement: bool` flag
with AST-level callsite scan).

**Medium findings:** M-R2-1 (case-A vs case-B differentiation; AC2.7
`_pending_sell_age_seconds` watchdog); M-R2-2 (`on_position_closed` 4
close-path coverage); M-R2-3 (mtime + content freshness check);
M-R2-4 (Wilson upper-bound decision input); M-R2-5 (mandatory mid-sprint
Tier 3 review at S4a close-out).

**Low findings:** L-R2-1 (SbC #20/#21 rephrasing from "definitively
impossible" to "judged-not-worth-the-marginal-complexity"); L-R2-2
(DEC-390 multi-position-on-symbol restart attribution); L-R2-3
(cumulative diff bound recalibration).

**Disposition outcome:** 14 of 14 findings accepted (10 in full,
4 with different/partial fix shape). A14 fired → Phase A re-entry
required per Outcome C.

### Phase A Tier 3 review #1 (2026-04-29) — verdict REVISE_PLAN

**Trigger:** `protocols/adversarial-review.md` v1.1.0 § Outcome C —
independent design review during Phase A re-entry. Tier 3 trigger #5
(Adversarial review N≥2) and trigger #1 (safety-load-bearing footprint)
independently fire.

**Verdict:** REVISE_PLAN. The FAI's self-falsifiability clause fires.

**Sub-area A finding (drove REVISE_PLAN):** Missing primitive-semantics
assumption — callback-path bookkeeping atomicity. The L3 ceiling check
reads two attributes (`pending`, `sold`) and adds `requested`. If a
callback path (e.g., `on_fill` processing a partial fill) yields between
`pending -= filled_qty` and `sold += filled_qty`, another coroutine's
ceiling check sees `pending` already decremented but `sold` not yet
incremented — total is artificially low — and a SELL that should be
blocked passes. This is exactly the structural class FAI #1 exists to
prevent, but FAI #1's AST guard + mocked-await injection test are scoped
narrowly to `_reserve_pending_or_fail`. **This is the third FAI-class
finding.**

**Tier 3 mandates (5 items A–E):**

- **Item A:** Add FAI entry #9 (callback-path bookkeeping atomicity).
- **Item B:** Extend H-R2-1's atomic-reserve protection to ALL bookkeeping
  callback paths (`on_fill`, `on_cancel`, `on_reject`, `_on_order_status`,
  AND `_check_sell_ceiling` multi-attribute read).
- **Item C:** C-R2-1 + H-R2-2 coupling — under H1 active AND
  `Broker.refresh_positions()` failure, mark position
  `halt_entry_until_operator_ack=True`.
- **Item D:** Cross-layer composition tests at ≥4 (Tier 3 floor; above
  template's "at least one"); CL-6 deferral rationale required.
- **Item E:** `SimulatedBrokerWithRefreshTimeout` fixture for in-process
  Branch 4 testing.

**6 DEFs filed by Tier 3:**

- **DEF-FAI-CALLBACK-ATOMICITY** — sprint-gating; Round 3 advancement
  gated on this DEF.
- **DEF-CROSS-LAYER-EXPANSION** — cross-layer composition tests at floor
  rather than coverage-comprehensive.
- **DEF-FAI-N-INCREASE** — FAI #5 N=30 → N=100.
- **DEF-FAI-2-SCOPE** — FAI #2 high-volume axis OUT of Sprint 31.92.
- **DEF-FAI-8-OPTION-A** — FAI #8 option (a) over (b).
- **DEF-SIM-BROKER-TIMEOUT-FIXTURE** — `SimulatedBroker` cannot exercise
  Branch 4; fixture variant required.

**2 RSKs filed by Tier 3:**

- **RSK-FAI-COMPLETENESS** (MEDIUM) — FAI's self-falsifiability clause
  triggered; Round 3 may surface a fourth.
- **RSK-CROSS-LAYER-INCOMPLETENESS** (MEDIUM) — cross-layer test count
  at template floor; DEC-386's empirical falsification justifies
  heightened bar.

### Phase B re-run + Phase C re-revision (2026-04-29)

**Substantive vs Structural Rubric** (from `protocols/adversarial-review.md`
v1.1.0 §"Substantive vs Structural decision rubric") fired **5 of 8
triggers** — Phase B re-run mandatory:

- Trigger #1 (Hypothesis Prescription modification — H-R2-2 halt-or-proceed
  gate tightened with N=100 hard gate).
- Trigger #2 (FAI modification — entry #9 NEW; entries #3/#5/#8 status
  promoted from "measured-only" / "unverified" to
  "unverified-with-falsifying-spike-scheduled").
- Trigger #6 (session breakdown additions — S4a-ii NEW; S5c NEW; 10 → 13
  sessions).
- Trigger #7 (NEW RSK at MEDIUM-HIGH or higher — RSK-RECONSTRUCTED-POSITION-DEGRADATION
  re-rated MEDIUM-HIGH per Severity Calibration Rubric).
- Trigger #8 (halt-or-proceed gate language modified — N=100 hard gate
  for `h1_propagation_zero_conflict_in_100`).

**7 settled operator decisions** (per Phase B re-run prompt):

| # | Decision | Effect |
|---|----------|--------|
| 1 | FAI #3 adversarial sub-spike — worst-axis Wilson UB | S1a script extended; JSON gains `adversarial_axes_results`, `worst_axis_wilson_ub` |
| 2 | FAI #5 N=30 → N=100 hard gate | S1a script extended; JSON gains `h1_propagation_n_trials=100`, `h1_propagation_zero_conflict_in_100: bool` |
| 3 | FAI #8 option (a) — 3 reflective-call sub-tests | S4a-ii adds `**kw` unpacking, computed-value flag, `getattr` reflective access |
| 4 | M-R2-1 watchdog auto-activation (NOT manual) | `pending_sell_age_watchdog_enabled: auto` flips to `enabled` on first `case_a_in_production` event |
| 5 | 5 cross-layer composition tests (CL-1 through CL-5) + `SimulatedBrokerWithRefreshTimeout` fixture | S5c NEW SESSION; CL-6 OUT |
| 6 | Sprint 31.94 D3 prioritization — separate Discovery activity | Out of Sprint 31.92 scope |
| 7 | Round 3 outcome pre-commitment | Reproduced verbatim in § 1 above; binding |

**5 Tier 3-mandated revisions A–E** all materialized into Phase C
artifacts 1–8 (sealed at the end of the prior session).

---

## 4. The Revised Falsifiable Assumption Inventory (verbatim, 9 entries)

> **Reproduced verbatim from `falsifiable-assumption-inventory.md` (Phase
> C revised) per Phase C generation prompt § Quality bars: "The FAI must
> appear verbatim. No paraphrasing. The self-falsifiability clause is
> load-bearing per process-evolution lesson F.6."**

### Origin (preserved verbatim from Phase A re-entry)

Round 1 caught the asyncio yield-gap race (a primitive-semantics
assumption — the implicit claim that asyncio's single-threaded event loop
serialized concurrent emit-side calls). Round 2 caught the `ib_async`
position-cache freshness assumption (the implicit claim that
`broker.get_positions()` returned fresh broker state). Phase A Tier 3
caught the callback-path bookkeeping atomicity assumption (the implicit
claim that the H-R2-1 atomic-reserve protection was sufficient to
guarantee L3 ceiling correctness). All three are primitive-semantics
assumptions whose violation silently produced the symptom class the
proposed fix claimed to address. Per `protocols/adversarial-review.md`
v1.1.0 § Outcome C, the recurrence of the same primitive-semantics class
across consecutive rounds returns the sprint to Phase A; this inventory
is the structural defense.

### Inventory falsifiability (preserved load-bearing clause)

Per `templates/sprint-spec.md` v1.2.0 § Falsifiable Assumption Inventory,
this inventory is itself a falsifiable artifact. **If Round 3 (or any
subsequent review) finds an additional primitive-semantics assumption
load-bearing on the proposed mechanism not in this list, the inventory
has failed — and the mechanism's adversarial-review verdict must be
downgraded accordingly.** Phase A Tier 3 already exercised this clause
once (entry #9 added); Round 3 full-scope cross-check is the next
defense layer.

### Inventory (9 entries)

| # | Primitive-semantics assumption | Falsifying spike or test | Status |
|---|--------------------------------|--------------------------|--------|
| 1 | asyncio guarantees that synchronous Python statements between two `await` points (or in a coroutine body without any `await`) execute atomically with respect to other coroutines on the same event loop. The C-1 reservation pattern's correctness depends on `_reserve_pending_or_fail`'s body remaining synchronous post-refactor (no `await` between ceiling-check and reserve increment). **NOTE:** entry #9 extends this assumption to all callback paths that mutate the bookkeeping counters; entry #1 covers the place-time emit path specifically. | (a) **AST-level scan** in regression suite asserts no `ast.Await` node within `_reserve_pending_or_fail`'s body — `ast.parse(textwrap.dedent(inspect.getsource(om._reserve_pending_or_fail)))` walked for `ast.Await`; assertion fails on any await. (b) **Mocked-await injection test:** monkey-patch the implementation to insert `await asyncio.sleep(0)` between check and reserve, then assert the race IS observable under injection. The injection test is mechanism-sensitive: if the test still refuses the second coroutine even with the injection, the protection is verifying outcome only and the test is unsound. | **unverified — falsifying spike scheduled in S4a-i.** Will become **falsified** on first green S4a-i regression run. |
| 2 | `ib_async`'s position cache catches up to broker state within `Broker.refresh_positions(timeout_seconds=5.0)` under all observed reconnect-window conditions. AC2.5's refresh-then-verify mechanism's correctness depends on this. **High-volume steady-state behavior under hundreds of variants is explicitly out of Sprint 31.92 scope per Tier 3 item D / Decision 5 / DEF-FAI-2-SCOPE — deferred to Sprint 31.94 reconnect-recovery.** | **S3b sub-spike** (per C-R2-1 disposition): simulate Gateway disconnect/reconnect during paper hours; measure `cache_staleness_p95_ms`, `cache_staleness_max_ms`, `refresh_success_rate`, `refresh_p95_ms` across N≥10 disconnect/reconnect cycles. **Halt-or-proceed gate:** if `cache_staleness_max_ms > refresh_timeout_seconds × 1000` in any trial, the chosen fix is itself unreliable; halt and surface to operator. **Branch 4** (`verification_stale: true` alert) is the structural defense if measurement reveals non-convergent cases — preserves safety even when the spike falsifies. **`SimulatedBrokerWithRefreshTimeout` fixture (S5c) enables in-process Branch 4 unit testing; without the fixture Branch 4 is unreachable in `SimulatedBroker` per Tier 3 #B2 / Decision 5 / DEF-SIM-BROKER-TIMEOUT-FIXTURE.** | **unverified — falsifying spike scheduled in S3b; Branch 4 fallback + `SimulatedBrokerWithRefreshTimeout` fixture (S5c) are load-bearing defenses.** Status flips to **falsified** on first green S3b paper spike + green S5c CL-3 + green Branch 4 unit test. |
| 3 | IBKR's `modifyOrder` rejection rate is stable at ≤5% steady-state AND remains stable under adversarial conditions (concurrent amends across positions; amends during reconnect window; amends on stale order IDs). The H2 mechanism selection's correctness depends on the determinism claim, NOT just the steady-state rate. | **S1a adversarial sub-spike (per Decision 1 / DEF-FAI-N-INCREASE).** S1a script extended to exercise three adversarial axes: (i) concurrent amends across N≥3 positions, (ii) amends during a Gateway reconnect window, (iii) amends with intentionally stale order IDs. Each axis produces its own rejection-rate distribution. **Halt-or-proceed gate uses the worst-axis Wilson UB**, NOT the steady-state UB. JSON output schema includes `adversarial_axes_results` and `worst_axis_wilson_ub`. | **unverified — falsifying spike scheduled in S1a.** Will become **falsified** on green S1a run if worst-axis Wilson UB satisfies the H2 < 5% / H4 5–20% / H1 ≥20% selection rule per Hypothesis Prescription. |
| 4 | The S1b substring fingerprint catches every variant of the locate-rejection error string IBKR can produce. AC2.1's case-B detection's correctness depends on this. | S1b substring-fingerprint validation across ≥5 symbols × ≥10 trials in the paper-account configuration; halts if observed strings disagree. Sampling is bounded to a single account, single Gateway version, single configuration. | **measured-only** — sampling within configuration only. Truly falsifying would require cross-version / cross-config sampling, which is out of scope for paper-trading validation. **Acceptable as measured-only because** the M-R2-1 case-A watchdog (AC2.7 `_pending_sell_age_seconds`) is **auto-activated** on first observed case-A in production paper trading per Decision 4 (`config/order_management.yaml: pending_sell_age_watchdog_enabled: auto` flips to `enabled` on first `case_a_in_production` event; NOT manual operator activation). The watchdog provides the structural fallback for any unmodeled string variant. |
| 5 | `cancel_all_orders(symbol, await_propagation=True)` synchronously confirms all bracket-child cancellations broker-side before returning. The H1 fallback path's correctness depends on this — without broker-side confirmation, the post-cancel SELL emission can collide with still-active bracket children (OCA conflict; locate suppression; or worse, both). | **S1a strengthened cancel-then-immediate-SELL stress (per Decision 2 / DEF-FAI-N-INCREASE — N=30 → N=100).** S1a script: (a) issue `cancel_all_orders(symbol, await_propagation=True)`; (b) immediately attempt SELL emission (`reqId+1` SELL within ≤10ms of the cancel return); (c) verify across **N=100 trials** that no bracket-child OCA conflict, locate suppression, or position state inconsistency surfaces. **HARD GATE: if even 1 trial in 100 exhibits a conflict, H1 is NOT eligible regardless of `modifyOrder` Wilson UB.** This is a hard gate, not advisory. JSON output schema includes `h1_propagation_n_trials=100` and `h1_propagation_zero_conflict_in_100: bool`. This sub-spike is also the structural defense for the H-R2-2 H1-fallback-locate-reject branch — if H1 is unsafe under cancellation-not-yet-propagated conditions, the composite failure mode is worse than what H-R2-2 currently models. | **unverified — falsifying spike scheduled in S1a.** Will become **falsified** on green S1a run if `h1_propagation_zero_conflict_in_100 == true`. Hard-gated; any non-zero conflict count rules H1 out regardless of other measurements. |
| 6 | IBKR raises a locate-rejection exception (case B) on hard-to-borrow symbols rather than silently holding the order pending borrow (case A). AC2.1's exception-handler-based detection depends on this. | **S1b explicit case-A vs case-B differentiation** (per M-R2-1 disposition): output JSON includes `case_a_observed: bool`, `case_a_count: int`, `case_b_count: int`, `case_a_max_age_seconds: int`. The spike actively probes for case A — the breaking condition for the assumption — by submitting hard-to-borrow orders and watching for the order accepted-but-held outcome. **Conditional defense:** if case A is observed, AC2.7 `_pending_sell_age_seconds` watchdog activates immediately. **Decision 4 strengthening:** even if S1b does NOT observe case A, the watchdog is `auto`-mode and flips to `enabled` on first observed `case_a_in_production` event. | **unverified — falsifying spike scheduled in S1b.** The spike is genuinely falsifying (probes for the breaking condition); status flips to **falsified** on S1b green run regardless of which case is observed (because the spike output is itself the falsification record). |
| 7 | `on_position_closed` event fires on all four ARGUS position-close paths: (a) broker confirms zero shares; (b) `_flatten_pending` clears; (c) `ManagedPosition` removed from active-positions dict; (d) the canonical `on_position_closed` close-path itself. AC2.6's suppression-dict-clear mechanism's correctness depends on this. | **M-R2-2 regression test** exercises all four close paths and asserts the dict entry is cleared in each (`test_suppression_dict_cleared_on_all_position_close_paths`). If any path fails, S3b audit-and-fix-or-document: either the event must fire from all paths, OR the dict-clear logic subscribes to multiple events. | **unverified — falsifying spike scheduled in S3b.** Will become **falsified** on first green S3b regression run; if any close path fails the test, the disposition's "audit-and-fix-or-document" gate forces resolution before merge. |
| 8 | The H-R2-5 codebase scan for `is_stop_replacement=True` callers (Regression Checklist invariant 24) has no false-negative paths via reflective or aliased call patterns. The is-stop-replacement-only-from-`_resubmit_stop_with_retry`-normal-retry-path contract's enforcement depends on this. | **S4a-ii adversarial regression sub-tests (per Decision 3 / DEF-FAI-8-OPTION-A — option (a) chosen over (b)).** S4a-ii adds 3 reflective-call sub-tests probing whether the AST-level scan for `is_stop_replacement=True` callers catches: (a) `kw = {"is_stop_replacement": True}; om._check_sell_ceiling(..., **kw)` (`**kw` unpacking); (b) `flag = True; om._check_sell_ceiling(..., is_stop_replacement=flag)` (computed-value flag assignment); (c) `getattr(om, "_check_sell_ceiling")(..., is_stop_replacement=True)` (`getattr` reflective access). Each sub-test exercises the AST scanner against the reflective construct and asserts either detection-with-flag (preferred) or known-coverage-gap-documented (fallback). | **unverified — falsifying spike scheduled in S4a-ii.** Will become **falsified** on first green S4a-ii regression run. Option (b) accept-and-document **NOT TAKEN** per Decision 3. |
| 9 | **(NEW per Tier 3 item A — callback-path bookkeeping atomicity.)** All bookkeeping update paths on `cumulative_pending_sell_shares` and `cumulative_sold_shares` (place-side increment, cancel/reject decrement, partial-fill transfer, full-fill transfer, `_check_sell_ceiling` multi-attribute read) execute synchronously between bookkeeping read and write across the entire transition. The L3 ceiling correctness depends on the asyncio single-event-loop guarantee applying to **every path that mutates these counters, not only `_reserve_pending_or_fail`**. The `_check_sell_ceiling` check reads two attributes (`pending`, `sold`) and adds `requested`; if a callback path (e.g., `on_fill` processing a partial fill) yields between `pending -= filled_qty` and `sold += filled_qty`, another coroutine's ceiling check sees `pending` already decremented but `sold` not yet incremented — total is artificially low — and a SELL that should be blocked passes. This is exactly the structural class entry #1 exists to prevent, but entry #1's AST guard + mocked-await injection test are scoped narrowly to `_reserve_pending_or_fail`. | **S4a-ii AST-no-await scan + mocked-await injection regression extended to all callback paths that mutate the bookkeeping counters** (per Tier 3 items A + B / DEF-FAI-CALLBACK-ATOMICITY): `on_fill` (partial-fill transfer + full-fill transfer), `on_cancel` (decrement), `on_reject` (decrement), `_on_order_status` (status-driven mutations), and the `_check_sell_ceiling` multi-attribute read. Pattern-matches the entry #1 falsifying mechanism, applied across all 5 paths. The H-R2-1 disposition extension means the atomic-reserve protection is the **reference pattern**, and the same guard + injection test apply to every bookkeeping path. | **unverified — falsifying spike scheduled in S4a-ii.** Will become **falsified** on first green S4a-ii regression run. **Sprint-gating Round 3 advancement** per Tier 3 verdict — Round 3 reviewer's FAI cross-check explicitly confirms entry #9 + extended H-R2-1 protection. |

### Justification log for measured-only / unverified entries

The new template requires explicit per-entry justification when an entry
is **measured-only** or **unverified-without-falsifying-spike**. The
recommended Phase A actions are now SETTLED operator decisions; restated
compactly here for adversarial-review scrutiny:

- **#1 (asyncio synchronicity, narrow scope):** unverified at Phase C is
  normal — the falsifying mechanism is a regression test landing in S4a-i.
  No additional justification needed beyond "scheduled in session
  breakdown."
- **#2 (`ib_async` cache freshness):** unverified at Phase C; falsifying
  spike scheduled in S3b. Defense-in-depth via Branch 4 fallback +
  C-R2-1↔H-R2-2 coupling (`halt_entry_until_operator_ack=True` if H1
  active AND refresh fails) per Tier 3 item C. **`SimulatedBrokerWithRefreshTimeout`
  fixture (S5c) enables in-process Branch 4 unit testing per Tier 3 item
  E / Decision 5 / DEF-SIM-BROKER-TIMEOUT-FIXTURE.** **High-volume
  steady-state axis (DEF-FAI-2-SCOPE) explicitly out of Sprint 31.92 scope
  per Tier 3 item D — deferred to Sprint 31.94 reconnect-recovery; FAI #2
  scope-text amendment lands there.**
- **#3 (`modifyOrder` determinism):** unverified at Phase C; falsifying
  spike (adversarial sub-axes) scheduled in S1a per Decision 1.
  Worst-axis Wilson UB drives halt-or-proceed gate per Hypothesis
  Prescription. Operator chose to add the adversarial sub-spike rather
  than retain measured-only with RSK-S1A-ADVERSARIAL-UNTESTED MEDIUM-HIGH
  (the latter would have been a Round 3 re-litigation candidate).
- **#4 (locate-rejection string stability):** measured-only acceptable
  because **Decision 4** auto-activates the AC2.7 watchdog on first
  observed case-A in production paper trading (NOT manual operator
  activation). The watchdog is the structural fallback for any unmodeled
  string variant.
- **#5 (`await_propagation` atomicity):** unverified at Phase C;
  falsifying spike (cancel-then-immediate-SELL stress at N=100) scheduled
  in S1a per Decision 2. **Hard gate:** any conflict in 100 trials → H1
  NOT eligible regardless of `modifyOrder` Wilson UB. N increased from
  ≥30 to N=100 per Tier 3 sub-area B finding (Wilson UB on 0/30 is roughly
  [0%, 11.6%] — all-30-green still permits ~1-in-9 production failures;
  N=100 tightens the bound).
- **#6 (locate-rejection exception vs held order):** unverified at Phase
  C; falsifying spike actively probes for the breaking condition. Strong
  falsifiability — no escalation. Decision 4 watchdog auto-activation is
  the additional structural defense.
- **#7 (`on_position_closed` completeness):** unverified at Phase C;
  falsifying regression scheduled in S3b. Strong falsifiability — no
  escalation.
- **#8 (AST callsite scan completeness):** unverified at Phase C;
  falsifying mechanism scheduled in S4a-ii per Decision 3 (option (a)
  adversarial regression sub-tests over option (b) accept-and-document).
- **#9 (callback-path bookkeeping atomicity, NEW):** unverified at Phase
  C; falsifying mechanism scheduled in S4a-ii per Tier 3 items A + B.
  **Sprint-gating Round 3 advancement.**

### Out of scope (deliberately not in this inventory)

For Round 3 reviewer reference. The following are **not** primitive-
semantics assumptions and are explicitly excluded from this inventory:

- **Operator-process assumptions** (e.g., "operator will see and
  acknowledge the alert" for H-R2-2 HALT-ENTRY; "operator will run
  daily-flatten script" for RSK-RECONSTRUCTED-POSITION-DEGRADATION).
  These are process risks tracked in the RSK list per Severity
  Calibration Rubric, not primitive-semantics.
- **System-design choices** (e.g., "stop-replacement bypassing the
  ceiling cannot itself produce over-flatten" for H-R2-5; "HALT-ENTRY
  rather than auto-recovery is the correct posture" for H-R2-2). These
  are design decisions tracked in DEC entries, not primitive-semantics.
- **Statistical-inference choices** (e.g., "Wilson UB at 95% confidence
  is the right asymmetric-conservative bound" for M-R2-4). These are
  methodological choices, not claims about primitive runtime behavior.
- **Architectural-closure assumptions for prior sprints** (e.g., DEC-386's
  4-layer OCA defense; DEC-388's 5-layer alert observability). These were
  validated/falsified within Sprint 31.91 and are not Sprint-31.92-load-bearing.
  However, **DEC-386 was empirically falsified on 2026-04-28 (60 NEW
  phantom shorts via cross-layer composition path);** Sprint 31.92 is the
  response. This inventory does not re-litigate DEC-386's per-layer
  assumptions but does include the `ib_async` cache primitive (#2) that
  the empirical falsification surfaced.
- **CL-6 cross-layer composition (rollback + locate-suppression
  interaction)** per Decision 5 — explicitly OUT of Sprint 31.92 scope;
  deferred with rationale documented in `docs/process-evolution.md`.
  CL-1 through CL-5 cover the cross-layer compositions Tier 3 sub-area D
  considered operationally relevant.

---

## 5. Round 3 Reviewer's FAI-Specific Tasks

Per `protocols/adversarial-review.md` v1.1.0 §"Probing Sequence" item 1
(Assumption Mining → Falsifiable Assumption Inventory cross-check),
Round 3 reviewer must perform the following FAI-specific tasks. These
are mandatory because Sprint 31.92 is safety-load-bearing and authored
an FAI per `protocols/sprint-planning.md` v1.3.0 step 9.

### Task 1 — Completeness check (the primary falsification probe)

Identify any primitive-semantics assumption load-bearing on the proposed
mechanism that is NOT in the FAI's 9 entries. **Sibling-class probing is
mandatory.** Specifically, ask:

- Are there surfaces in the proposed mechanism that depend on runtime
  behavior of asyncio primitives (event loop, coroutine yield, task
  cancellation, queue ordering) that are NOT in entries #1 or #9?
- Are there surfaces in the proposed mechanism that depend on runtime
  behavior of `ib_async` primitives (cache freshness, event ordering,
  reconnect handling, subscription lifecycle) that are NOT in entry #2?
- Are there surfaces in the proposed mechanism that depend on runtime
  behavior of IBKR API primitives (`modifyOrder`, `cancel_all_orders`,
  `place_order`, locate-rejection error reporting) that are NOT in
  entries #3, #5, #6?
- Are there surfaces that depend on event-firing completeness (`on_fill`,
  `on_cancel`, `on_reject`, `on_position_closed`) beyond entries #7 and #9?
- Are there surfaces that depend on AST-scan completeness (callsite
  detection of `is_stop_replacement=True`) beyond entry #8?
- Are there surfaces that depend on broker-side propagation atomicity
  beyond entry #5?

**Per the inventory's self-falsifiability clause, any new primitive-
semantics assumption surfaced indicates the inventory has failed.**
Phase A Tier 3 already exercised this clause once (entry #9 added
2026-04-29). Round 3 is the next layer.

**Routing:** A finding here routes per Decision 7 (a) — primitive-
semantics-class Critical → another revision pass (Phase A re-entry per
Outcome C).

### Task 2 — Status-rating audit

For each entry, scrutinize the declared status (verified / falsified /
unverified-with-falsifying-spike-scheduled / measured-only). The
template reminds: *"measured-only spikes are the failure mode this
section exists to prevent."* Specifically:

- **Entry #4 (measured-only)** — verify the Decision 4 auto-activation
  justification holds: is `pending_sell_age_watchdog_enabled: auto`
  semantics genuinely atomic at first `case_a_in_production` event? Does
  the auto-flip survive ARGUS restart? What if the event fires during a
  partial-init window?
- **Entries #1, #2, #3, #5, #6, #7, #8, #9 (unverified-with-falsifying-spike-scheduled)** —
  verify each session-breakdown reference points to a real session that
  actually delivers the falsifying mechanism (S1a / S1b / S3b / S4a-i /
  S4a-ii / S5c). Cross-check against `session-breakdown.md` for matching
  session IDs.

All three Round-2 ESCALATION FLAGS (entries #3, #5, #8) are now rated
unverified-with-falsifying-spike-scheduled per the settled operator
decisions; entry #4 remains measured-only with explicit Decision-4
auto-activation justification.

### Task 3 — Spike-quality check

For each **unverified** entry with a scheduled falsifying spike, verify
the spike actually falsifies (probes for breaking conditions) rather
than measures (samples normal conditions). Specifically:

- **Entry #1 (S4a-i):** AST scan walks `_reserve_pending_or_fail`'s body
  for `ast.Await` nodes; assertion fails on any await. Mocked-await
  injection test inserts `await asyncio.sleep(0)` between check and
  reserve and asserts the race IS observable under injection. **Verify
  the injection test is mechanism-sensitive: if the test still refuses
  the second coroutine even with the injection, the protection is
  verifying outcome only and the test is unsound.**
- **Entry #3 (S1a):** Confirm S1a's adversarial axes (concurrent /
  reconnect / stale-ID amends) actually attempt to break the determinism
  claim under stress conditions where the failure mode would manifest,
  not just steady-state sampling.
- **Entry #5 (S1a):** Confirm N=100 cancel-then-immediate-SELL stress
  with ≤10ms gap actually exercises the propagation-not-yet-converged
  condition. **Hard gate:** if even 1 trial in 100 exhibits a conflict,
  H1 is NOT eligible regardless of `modifyOrder` Wilson UB.
- **Entry #8 (S4a-ii):** Confirm the 3 reflective-call sub-tests
  (`**kw` unpacking; computed-value flag; `getattr` reflective access)
  actually probe for AST-scan false-negative paths.
- **Entry #9 (S4a-ii):** Confirm the AST-no-await scan + mocked-await
  injection pattern is applied across ALL 5 callback paths
  (`_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`,
  `_on_order_status`) AND that the multi-attribute read in
  `_check_sell_ceiling` is included.

### Task 4 — Cross-Layer Composition Test count + CL-6 deferral rationale

Per `templates/sprint-spec.md` v1.2.0, when DEC entries claim N≥3 layer
defense, regression checklist MUST include cross-layer composition
tests. **Sprint 31.92 commits to 5 tests (CL-1 through CL-5) per
Decision 5** — above the template's "at least one" floor; above Tier 3
sub-area D's 3-test floor.

**Round 3 reviewer should evaluate:**

- Is 5 the right count, or should there be more given DEC-386's
  empirical falsification (60 phantom shorts via cross-layer path that
  no single-layer test exercised)?
- Is **CL-6 (rollback + locate-suppression interaction)** deferral
  rationale (process-evolution lesson F.7, documented in
  `docs/process-evolution.md`) sufficient — i.e., is the trade-off
  between exhaustive coverage and bounded session count correctly
  resolved at "L4's compositions with runtime layers (other than CL-2)
  are weakly meaningful in the operationally-relevant case"? Or does
  production-relevance argue for inclusion?
- Does the `SimulatedBrokerWithRefreshTimeout` fixture
  (DEF-SIM-BROKER-TIMEOUT-FIXTURE) make Branch 4 reachable in-process
  for CL-3, OR does the fixture's in-process simulation diverge from
  production refresh-timeout behavior in a way that invalidates CL-3's
  cross-layer falsification?

### Task 5 — Synchronous-update invariant scope check

Does the AST-no-await scan + mocked-await injection regression test
apply to ALL bookkeeping callback paths per Tier 3 items A + B? Are
reflective patterns covered per DEF-FAI-8-OPTION-A?

**Specifically verify:**

- Regression invariant 23 (per `regression-checklist.md`) covers:
  `_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`,
  `_on_order_status`, AND the `_check_sell_ceiling` multi-attribute
  read sequence.
- AST scan is robust against the 3 reflective patterns per Decision 3:
  `**kw` unpacking, computed-value flag, `getattr` reflective access.
- Mocked-await injection test is mechanism-sensitive (i.e., asserts
  the race IS observable under injection, not merely that the outcome
  is preserved).

### Task 6 — Defense-in-depth probe (sibling-class assumption mining)

Beyond the FAI's 9 entries, mine for primitive-semantics assumptions in
adjacent surfaces that this sprint touches but the FAI may not have
listed:

- **`Broker.refresh_positions(timeout_seconds=5.0)` ABC method** (NEW per
  C-R2-1) — what runtime behavior does this depend on? FAI #2 covers
  the cache-freshness assumption; are there OTHER assumptions (event
  ordering, error semantics, partial-failure behavior, network-timeout
  vs. exception-timeout)?
- **`IBKRConfig.bracket_oca_type` runtime-flippability** (preserved per
  DEC-386 design intent) — does the runtime flip semantic depend on a
  primitive that's unverified?
- **`--allow-rollback` CLI flag** (NEW per AC4.7) — does the exit-code-2
  + stderr FATAL banner path depend on a primitive that's unverified?
- **`pending_sell_age_watchdog_enabled: auto`** (NEW per Decision 4) —
  the auto→enabled flip semantic at first `case_a_in_production` event
  depends on assumptions about config field mutation atomicity and
  restart-survival.
- **AC2.7 `_pending_sell_age_seconds` watchdog** — what assumptions
  does the watchdog firing semantic depend on (timer accuracy under
  load, event-loop lag, etc.)?

Surface any new primitive-semantics findings as Critical-of-FAI-class
under Decision 7 (a) routing.

---

## 6. Round 3 Probing Sequence (full per `protocols/adversarial-review.md` v1.1.0)

Beyond the FAI-specific tasks above, Round 3 reviewer applies all 6
probing-sequence steps at full scope:

### Step 1 — Assumption Mining

> "What assumptions is this spec making that could be wrong? List every
> implicit assumption — about data, about user behavior, about system
> state, about dependencies, about performance."

Plus the FAI cross-check tasks above.

### Step 2 — Failure Mode Analysis

> "What are the failure modes? For each component or operation in this
> spec, what happens when it fails? Are there cascade failures? Are there
> states that are hard to recover from?"

Specifically probe:

- Path #1 mechanism failure modes under each of H2 / H4 / H1 selection
  (AC1.2 conditional variants).
- Path #2 detection failure modes when `_is_locate_rejection()` returns
  False on a real locate-rejection (FAI #4 measured-only path).
- L3 ceiling failure modes when `_reserve_pending_or_fail` is called
  on a `ManagedPosition` whose state is concurrently being mutated by
  a callback path (FAI #9 scope).
- L4 rollback failure modes when `bracket_oca_type=0` is set without
  `--allow-rollback` (AC4.7 exit-code-2 path) AND when set WITH it
  (AC4.6 dual-channel CRITICAL warning path).
- Branch 4 (`verification_stale: true`) failure modes when refresh
  timeout fires AND H1 is the active mechanism (Tier 3 item C
  `halt_entry_until_operator_ack=True` coupling).

### Step 3 — Future Regret

> "What will we regret about this design in 3 months? In 6 months? What
> doors does this close? What technical debt does this introduce?"

Specifically probe:

- `is_reconstructed: bool = False` refusal posture — Sprint 31.94 D3
  is bounded by 2 weeks (Sprint Abort Condition #7 trigger lowered per
  H-R2-3). What happens if Sprint 31.94 D3 slips?
- `--allow-rollback` CLI flag — does this become operational debt that
  bleeds into future sprints (every emergency rollback requires
  operator-typed flag; every CI run that wants to test rollback path
  requires the flag)?
- Cross-layer test count at 5 (CL-1 through CL-5) — deferred CL-6
  becomes a known gap. Will Sprint 31.93 + 31.94 inherit it?
- FAI infrastructure — is this becoming a perpetual checklist that
  grows with every sprint, or does it stabilize?

### Step 4 — Specification Gaps

> "What is underspecified? Where will the implementer have to make
> judgment calls that could go wrong? What edge cases are not addressed?"

Specifically probe:

- AC2.5 three-branch + Branch 4 classification — is Branch 3 ("broker
  shows short OR quantity divergence OR unknown side") sufficiently
  specified? What's the disambiguation between "broker shows short" and
  "broker shows quantity divergence with negative shares"?
- AC3.1 5-state-transition synchronous-update invariant — is the partial-
  fill-then-full-fill ordering sequence specified? What if `on_fill`
  fires twice for the same fill due to broker re-emission?
- AC4.6 dual-channel CRITICAL warning — is the operator-acknowledgment
  semantic specified, or does ARGUS proceed silently after emitting?
- Decision 4 auto-activation event semantic — what defines a
  `case_a_in_production` event? Is it the first observed instance
  per-position, per-symbol, per-day, or globally?

### Step 5 — Integration Stress

> "How does this interact with existing systems? What existing behavior
> could this break? What existing assumptions does this violate?"

Specifically probe:

- DEC-117 atomic-bracket invariants (preserved per AC4.5) — does the
  L3 ceiling with `is_stop_replacement: bool` flag introduce a new
  exemption path that DEC-117's invariant doesn't anticipate?
- DEC-369 broker-confirmed reconciliation immunity — does AC3.6 + AC3.7
  composing additively with DEC-369 introduce a new failure mode at
  the intersection (e.g., reconstructed position that's also broker-
  confirmed)?
- DEC-372 stop retry caps — does AC1.3 (mechanism applied to
  `_resubmit_stop_with_retry` emergency-flatten branch) interact with
  DEC-372's exponential-backoff retry pattern?
- DEC-385 `phantom_short_retry_blocked` alert path — does Branch 3 +
  Branch 4 reuse compose correctly with DEC-385's existing 6-layer
  contract?
- DEC-388 `POLICY_TABLE` 14th entry (`sell_ceiling_violation`) — does
  the AST exhaustiveness regression guard (per AC3.9) correctly reject
  `POLICY_TABLE` with 13 entries (existing) AND with 15+ entries (future
  additions)?

### Step 6 — Simulated Attack (security-relevant axis)

> "If someone wanted to exploit this design, how would they do it? What
> is the attack surface?"

Sprint 31.92 is not directly security-sensitive in the cyber sense, but
the operator-pre-commitment axis bears probing:

- Could a misbehaving operator-typed `--allow-rollback` flag (e.g., in a
  startup script copied across environments) silently downgrade ARGUS
  from DEC-386's 4-layer OCA enforcement to DEC-386 ROLLBACK ACTIVE
  state without operator awareness?
- Could an operator who dismisses the AC4.6 dual-channel CRITICAL
  warning at startup miss the indication that `bracket_oca_type=0` is
  active?
- Could a misbehaving CI workflow run with `--allow-rollback` in test
  fixtures bleed into production startup?

---

## 7. Architecture Document Excerpts (substituted with Sprint Spec
authoritative descriptions per § Phase C consistency note)

> **Per § Phase C consistency note above:** `docs/architecture.md` was not
> uploaded with the Phase C artifact set. The sections below substitute
> the Sprint Spec's Deliverables 1–4 + corresponding Acceptance Criteria
> as the authoritative description of the architectural surfaces this
> sprint modifies. Round 3 reviewer should additionally read the actual
> `docs/architecture.md` §3.3 / §3.7 / §13 from the repo at
> `https://github.com/stevengizzi/argus.git` HEAD to ground the design
> review in pre-change code surfaces.

### §3.3 Broker abstraction — surfaces modified by this sprint

**From `sprint-spec.md` Deliverable 2 (verbatim, lines 56–72):**

> **Path #2 detection + position-keyed locate-rejection suppression with
> broker-verified timeout (L2 — `_flatten_position`, `_trail_flatten`,
> `_check_flatten_pending_timeouts`, `_escalation_update_stop`
> exception handlers).** Add `_LOCATE_REJECTED_FINGERPRINT` substring
> constant + `_is_locate_rejection()` helper in `argus/execution/ibkr_broker.py`
> mirroring DEC-386's `_is_oca_already_filled_error` pattern; add
> `OrderManager._locate_suppressed_until: dict[ULID, float]` keyed by
> `ManagedPosition.id` (NOT symbol — cross-position safety per
> Round-1 H-2). Wire suppression detection at `place_order` exception
> in 4 standalone-SELL paths with pre-emit suppression check.
> Suppression-timeout fallback queries broker for actual position state
> BEFORE alert emission (Round-1 H-3 + Round-2 C-R2-1) via new
> `Broker.refresh_positions(timeout_seconds=5.0)` ABC method;
> three-branch classification (zero / expected-long / unexpected) + Branch 4
> (`verification_stale: true`) on refresh failure + HALT-ENTRY coupling
> under H1 active AND refresh failure (per Tier 3 item C).

**`Broker.refresh_positions()` ABC method (verbatim from `round-2-disposition.md`):**

```python
class Broker(ABC):
    @abstractmethod
    async def refresh_positions(self, *, timeout_seconds: float = 5.0) -> None:
        """Force broker-side position cache refresh. Blocks until cache is
        synchronized with broker state OR timeout expires. AC2.5 prerequisite.
        """
        ...

class IBKRBroker(Broker):
    async def refresh_positions(self, *, timeout_seconds: float = 5.0) -> None:
        end_event = asyncio.Event()
        def _on_position_end():
            end_event.set()
        self._ib.positionEndEvent += _on_position_end
        try:
            self._ib.reqPositions()
            await asyncio.wait_for(end_event.wait(), timeout=timeout_seconds)
        finally:
            self._ib.positionEndEvent -= _on_position_end
```

This new ABC method composes with `Broker`'s existing
`get_positions()` / `place_order()` / `cancel_all_orders()` /
`cancel_order()` / `place_bracket_order()` surface. `SimulatedBroker`
gets a no-op implementation (returns immediately). `AlpacaBroker`
(incubator) gets a no-op or raises `NotImplementedError` (out of scope
for this sprint).

### §3.7 Order Manager — surfaces modified by this sprint

**From `sprint-spec.md` Deliverable 1 (verbatim, lines 47–55):**

> **Path #1 mechanism (L1 — `_trail_flatten`, `_resubmit_stop_with_retry`
> emergency-flatten branch, conditionally `_escalation_update_stop`).**
> Implement the S1a-spike-selected mechanism per Hypothesis Prescription
> hierarchy (H2 PRIMARY DEFAULT — amend bracket stop's `auxPrice` /
> H4 hybrid fallback — try amend, fall back to cancel-and-await on
> amend rejection / H1 last-resort — cancel-and-await before SELL).
> AMD-2 invariant framing is mechanism-conditional (preserved on H2;
> mixed on H4; superseded by AMD-2-prime on H1).

**From `sprint-spec.md` Deliverable 3 (verbatim, lines 73–96):**

> **Long-only SELL-volume ceiling with concurrency-safe pending-share
> reservation + reconstructed-position refusal posture (L3 — guarded at
> all 5 standalone-SELL emit sites; bracket placement EXCLUDED per H-1).**
> Add THREE fields on `ManagedPosition`: `cumulative_pending_sell_shares: int = 0`
> (incremented synchronously at place-time before `await`; decremented on
> cancel/reject; transferred to filled on fill — closes Round-1 C-1 asyncio
> yield-gap race), `cumulative_sold_shares: int = 0` (incremented at confirmed
> SELL fill), and `is_reconstructed: bool = False` (set True in
> `reconstruct_from_broker`; refusal posture for ARGUS-emitted SELLs per
> Round-1 C-2). Atomic `_reserve_pending_or_fail()` synchronous method per
> H-R2-1, with AST-no-await regression guard + mocked-await injection test.
> **Synchronous-update invariant extended to all bookkeeping callback paths
> per Tier 3 items A + B: `on_fill`, `on_cancel`, `on_reject`,
> `_on_order_status`, and `_check_sell_ceiling` multi-attribute read.**
> `_check_sell_ceiling()` accepts `is_stop_replacement: bool=False` per
> H-R2-5 — exemption permitted ONLY at `_resubmit_stop_with_retry` normal-retry
> path (AST callsite-scan regression guard with 3 reflective-call
> sub-tests per Decision 3 / FAI #8 option (a)). New `sell_ceiling_violation`
> alert type, `POLICY_TABLE` 14th entry (`operator_ack_required=True`,
> `auto_resolution_predicate=None`); AST exhaustiveness regression guard
> updated. AC2.7 `_pending_sell_age_seconds` watchdog **auto-activates** from
> `auto` to `enabled` on first observed `case_a_in_production` event per
> Decision 4.

**From `sprint-spec.md` Deliverable 4 (verbatim, lines 97–109):**

> **DEF-212 `_OCA_TYPE_BRACKET` constant drift wiring + operator-visible
> rollback warning + `--allow-rollback` CLI gate (L4).** `OrderManager.__init__`
> accepts `bracket_oca_type: int` keyword argument; `argus/main.py`
> construction call site passes `config.ibkr.bracket_oca_type`; 4
> occurrences of `_OCA_TYPE_BRACKET = 1` module constant replaced by
> `self._bracket_oca_type`; module constant deleted; grep regression guard.
> **Dual-channel CRITICAL warning** per H-R2-4 (combined): ntfy.sh
> `system_warning` urgent AND canonical-logger CRITICAL with phrase
> "DEC-386 ROLLBACK ACTIVE" when `bracket_oca_type != 1` AND
> `--allow-rollback` flag present. **Exit code 2 + stderr FATAL banner**
> when `bracket_oca_type != 1` AND `--allow-rollback` flag absent (AC4.7
> per H-R2-4). `IBKRConfig.bracket_oca_type` Pydantic validator UNCHANGED
> — runtime-flippability preserved per DEC-386 design intent.

**Key acceptance criteria the reviewer reads inline (selected verbatim
from `sprint-spec.md`):**

- **AC2.5** (broker-verified suppression-timeout fallback — three branches +
  Branch 4 + HALT-ENTRY coupling per Tier 3 item C) — see lines 190–214
  of `sprint-spec.md`.
- **AC3.1** (5 state transitions + synchronous-update invariant on ALL
  bookkeeping callback paths per Tier 3 items A + B) — see lines 233–257
  of `sprint-spec.md`.
- **AC3.5** (canonical C-1 race test + AST guards per Tier 3 items A + B) —
  see lines 279–284 of `sprint-spec.md`.
- **AC3.7** (`is_reconstructed` refusal posture) — see lines 290–295 of
  `sprint-spec.md`.
- **AC3.9** (`POLICY_TABLE` 14th entry) — see lines 300–303 of
  `sprint-spec.md`.
- **AC4.6** (dual-channel CRITICAL warning — H-R2-4 combined) — see lines
  325–335 of `sprint-spec.md`.
- **AC4.7** (`--allow-rollback` CLI flag gate per H-R2-4) — see lines
  336–344 of `sprint-spec.md`.

### §13 Alert Observability — surfaces modified by this sprint

**From `sprint-spec.md` AC3.9 (verbatim, lines 300–303):**

> **AC3.9 (`POLICY_TABLE` 14th entry):** `sell_ceiling_violation` policy
> entry: `operator_ack_required=True`, `auto_resolution_predicate=None`
> (manual-ack only). AST exhaustiveness regression guard updated to
> expect 14 entries.

The 14th entry composes additively with DEC-388's existing 13-entry
`POLICY_TABLE`. Existing 13 entries are unchanged. Existing
`phantom_short_retry_blocked` alert is REUSED at AC2.5 Branches 3 + 4
(DEC-385's emitter preserved verbatim). AST exhaustiveness regression
guard count must update from 13 → 14.

---

## 8. Adjacent DEC entries (excerpts from `sprint-spec.md` §"Relevant Decisions")

The following DEC entries from `docs/decision-log.md` are operationally
load-bearing for Sprint 31.92. Excerpts quoted verbatim from
`sprint-spec.md` §"Relevant Decisions" (lines 552–602) — the spec's
authoritative summary of how each DEC constrains Sprint 31.92:

### DEC-117 (Sprint 7) — Atomic Bracket Order Placement

> **DEC-117 (Sprint 7)** — Atomic bracket order placement. AC4.5 preserves
> this byte-for-byte. AC3.2 EXCLUDES bracket placement from ceiling check
> specifically to preserve DEC-117.

Constrains Sprint 31.92: T1 + T2 + bracket-stop atomicity preserved;
bracket placement excluded from L3 ceiling check; existing regression
test `test_dec386_oca_invariants_preserved_byte_for_byte` green
throughout S4b.

### DEC-369 (Sprint 27.95) — Broker-Confirmed Reconciliation

> **DEC-369 (Sprint 27.95)** — Broker-Confirmed Reconciliation. AC3.6
> must compose with broker-confirmed positions: `cumulative_pending_sell_shares
> = 0`, `cumulative_sold_shares = 0`, `is_reconstructed = True`
> initialization; refusal posture for ARGUS-emitted SELLs preserves
> DEC-369 immunity (broker-confirmed positions remain operator-managed).

Constrains Sprint 31.92: AC3.6 + AC3.7 compose additively with DEC-369;
both protections apply.

### DEC-372 (Sprint 27.95) — Stop Resubmission Cap

> **DEC-372 (Sprint 27.95)** — Stop Resubmission Cap with Exponential
> Backoff. The emergency-flatten branch in `_resubmit_stop_with_retry`
> (where retry cap is exhausted) is one of Path #1's surfaces. DEC-372's
> cap mechanism preserved; AC1.3 adds the H2/H4/H1 mechanism to the
> emergency SELL.

Constrains Sprint 31.92: AC1.3 extends Path #1 mechanism into
emergency-flatten branch; DEC-372 cap mechanism preserved.

### DEC-385 (Sprint 31.91) — Side-Aware Reconciliation Contract

> **DEC-385 (Sprint 31.91, 2026-04-02 → 2026-04-28)** — 6-layer Side-Aware
> Reconciliation Contract. The `phantom_short_retry_blocked` alert path
> (used by DEF-158 retry side-check) is re-used by Path #2's broker-verified
> suppression-timeout fallback (Branches 3 + 4). Constrains Sprint 31.92:
> DEF-158's 3-branch side-check (BUY/SELL/unknown) preserved verbatim;
> Path #2 adds NEW upstream detection at `place_order` exception, not a
> 4th branch.

Constrains Sprint 31.92: DEC-385 6-layer contract preserved byte-for-
byte; `phantom_short_retry_blocked` alert reused at AC2.5 Branches 3 + 4.

### DEC-386 (Sprint 31.91) — OCA-Group Threading + Broker-Only Safety

> **DEC-386 (Sprint 31.91 Tier 3 #1, 2026-04-27)** — 4-layer OCA-Group
> Threading + Broker-Only Safety. Closes DEF-204 OCA-cancellation race at
> IBKR layer. **Empirically falsified 2026-04-28** (60 NEW phantom shorts,
> debrief at `docs/debriefs/2026-04-28-paper-session-debrief.md`). DEC-386
> preserved unchanged; DEC-390 closes the residual paths structurally with
> concurrency-safe defense-in-depth. Constrains Sprint 31.92: S0/S1a/S1b/S1c
> surfaces preserved byte-for-byte; existing `# OCA-EXEMPT:` exemption
> mechanism re-used; existing `_is_oca_already_filled_error` re-used (NOT
> relocated this sprint); rollback escape hatch (`bracket_oca_type=0`)
> preserved with NEW startup-warning per AC4.6 + `--allow-rollback` CLI
> gate per AC4.7.

**`~98%` claim empirically superseded by DEC-390's structural closure;
rollback escape hatch preserved with new AC4.6 + AC4.7.** Per
process-evolution lesson F.5, Sprint 31.92's DEC-390 must use
**structural-closure framing** ("L1 closes Path #1 mechanism / L2
closes Path #2 detection + position-keyed suppression + broker-verified
timeout / L3 closes long-only ceiling with extended synchronous-update
invariant + reconstructed-position refusal / L4 closes constant-drift
hygiene with operator-visible rollback gate") rather than aggregate
percentage claims. Reviewer halts on tokens like "comprehensive,"
"complete," "fully closed," "covers ~N%."

### DEC-388 (Sprint 31.91) — Alert Observability Architecture

> **DEC-388 (Sprint 31.91, 2026-04-28)** — Alert Observability Architecture.
> New `sell_ceiling_violation` alert type added to `POLICY_TABLE` per
> AC3.9. Existing `phantom_short_retry_blocked` re-used per AC2.5.
> Constrains Sprint 31.92: must update `POLICY_TABLE` and AST exhaustiveness
> regression guard.

Constrains Sprint 31.92: `POLICY_TABLE` extended from 13 → 14 entries
(`sell_ceiling_violation` 14th); existing 13 entries unchanged; AST
exhaustiveness regression guard count updated.

### DEC-390 (proposed at sprint-close)

DEC-390 has not yet been written. Per AC6.1, it materializes at
sprint-close (D14 doc-sync) with four-layer structure: L1 Path #1
mechanism / L2 Path #2 fingerprint + position-keyed suppression +
broker-verified timeout / L3 SELL-volume ceiling with pending
reservation + reconstructed-position refusal + AC2.7 watchdog
auto-activation / L4 DEF-212 wiring + AC4.6 dual-channel + AC4.7
`--allow-rollback` gate. Cross-references to DEC-385, DEC-386, DEC-388,
DEF-204, DEF-212, Apr 28 paper-session debrief, S1a + S1b spike
artifacts, S5a + S5b + S5c validation artifacts.

---

## 9. Round 3 Verdict Template (per `protocols/adversarial-review.md` v1.1.0)

The reviewer fills in this template. Three Outcome states per protocol
§ Resolution.

### Outcome A — Round CLEAR (proceed to Phase D)

**Triggers when:**
- No Critical findings.
- ≤2 High findings.
- No primitive-semantics assumptions remain unverified or measure-only
  in the FAI.

**Output:** `adversarial-review-round-3-findings.md` documenting:
- Round CLEAR confirmation.
- All Medium and Low observations (applied directly to spec artifacts).
- Final FAI status (all entries falsified or measure-only-with-justification
  accepted).

**Routing:** Sprint planner proceeds to Phase D — implementation prompts
generated for S1a / S1b / S2a / S2b / S3a / S3b / S4a-i / S4a-ii / S4b /
S5a / S5b / S5c. Phase A re-entry NOT required.

### Outcome B — Round produced revisions (re-review required)

**Triggers when:**
- ≥1 Critical finding, OR
- ≥3 High findings.

**Output:** Disposition author summarizes findings that require spec
changes and proposes specific revisions to:
- `sprint-spec.md`
- `spec-by-contradiction.md`
- Any other affected artifacts.

**Routing per Decision 7 (binding):**

(a) **If the Critical finding is a foundational primitive-semantics miss
in the FAI's class** (asyncio yield-gap / `ib_async` cache freshness /
callback-path bookkeeping atomicity sibling) → **another revision pass
(Phase A re-entry per Outcome C)** is required. The FAI's
self-falsifiability clause has been triggered for the fourth time
(Round 1 / Round 2 / Phase A Tier 3 / Round 3 hypothetical). Phase B/C
re-run + Round 4 full-scope follow.

(b) **Any other Critical class** (edge case, missing test coverage,
design refinement, documentation gap, marginal scope concern) →
finding is **accepted as a known limitation, logged as RSK at
appropriate severity (MEDIUM-HIGH or higher per Severity Calibration
Rubric), and sprint ships to implementation.**

### Outcome C — Pattern of repeated Criticals (return to Phase A)

**Triggers when ANY of the following holds (per protocol verbatim):**
- ≥2 consecutive rounds produced Critical findings.
- The same primitive-semantics assumption *class* is caught in two
  consecutive rounds.
- ≥3 of the dispositions in any single round are PARTIAL ACCEPT
  (different fix shape).

**Note for Round 3:** Round 1 + Round 2 + Phase A Tier 3 already produced
Critical-of-FAI-class findings in three consecutive design-review steps.
A Round 3 Critical of the same class would be the **fourth** in the
cluster — Decision 7 (a) routes to Phase A re-entry, which is operationally
equivalent to Outcome C re-fire. Reviewer should flag the routing
explicitly.

**Note on Decision 7 (b) escape hatch:** Decision 7 (b) provides the
**non-FAI-class Critical** routing — accept-as-known-limitation +
RSK-and-ship. Reviewer should be explicit when invoking Decision 7 (b)
about why the finding is NOT FAI-class.

### Verdict template (reviewer fills in)

```
# Sprint 31.92 — Adversarial Review Round 3 — Findings

> Verdict author: [reviewer]
> Date: [YYYY-MM-DD]
> Outcome: [A / B / C]
> Decision 7 routing (if Outcome B with Critical): [(a) primitive-semantics-class
>   → Phase A re-entry / (b) any other Critical class → RSK + ship]
> A14 fired: [yes / no]

## Critical findings

### C-R3-N — [title]

**Severity:** Critical
**Primitive-semantics class:** [yes / no]  ← drives Decision 7 routing
**Affected FAI entries:** [list, or "none — new primitive-semantics surface"]

**Reviewer's argument:** [trace]

**Why this is FAI-class (or not):** [rationale]

**Proposed disposition:** [ACCEPT / PARTIAL ACCEPT (different) / REJECT]

**Proposed fix shape:** [if accepted]

## High findings

### H-R3-N — [title]

[same shape, severity High]

## Medium findings

### M-R3-N — [title]

[same shape, severity Medium]

## Low findings

### L-R3-N — [title]

[same shape, severity Low]

## FAI cross-check summary

- Completeness check: [pass / fail with C-R3-N]
- Status-rating audit: [pass / [list adjustments]]
- Spike-quality check: [pass / [list adjustments]]
- Cross-Layer Composition Test count + CL-6 deferral: [pass / fail]
- Synchronous-update invariant scope: [pass / fail]
- Defense-in-depth probe: [pass / [list new findings]]

## Verdict and routing

**Outcome:** [A / B / C]
**Decision 7 routing:** [N/A / (a) / (b)]
**Phase D status:** [proceed / NOT proceeding — Phase A re-entry required]
**Round 4 required:** [no / yes — narrowest possible scope (if Outcome B (b))
  / yes — full scope (if Outcome C)]
**Operator override:** [N/A / [explicit log entry]]
```

---

## 10. Cross-references

### DEFs filed at Phase A Tier 3 (6 total)

| DEF | Description | Sprint target |
|-----|-------------|---------------|
| DEF-FAI-CALLBACK-ATOMICITY | Extend AST-no-await guard + mocked-await injection regression to all bookkeeping callback paths | 31.92 (in-sprint) — sprint-gating Round 3 advancement |
| DEF-CROSS-LAYER-EXPANSION | Cross-layer composition tests at floor; commit to ≥4 with rationale | 31.92 Phase C re-run (5 tests CL-1 through CL-5 committed) |
| DEF-FAI-N-INCREASE | FAI #5 N=30 → N=100 hard gate | 31.92 S1a sub-spike refinement |
| DEF-FAI-2-SCOPE | FAI #2 high-volume axis OUT of 31.92; deferred to 31.94 | 31.92 (documentation) |
| DEF-FAI-8-OPTION-A | FAI #8 option (a) over (b) | 31.92 S4a-ii |
| DEF-SIM-BROKER-TIMEOUT-FIXTURE | `SimulatedBrokerWithRefreshTimeout` fixture for Branch 4 in-process testing | 31.92 S5c |

5 of 6 resolved in-sprint; 1 documented out-of-scope (DEF-FAI-2-SCOPE
deferred to Sprint 31.94 reconnect-recovery).

### RSKs filed (7 total)

**5 sprint-class (Round-1-revised):**

| RSK | Severity | Description |
|-----|----------|-------------|
| RSK-DEC-390-AMEND | MEDIUM | DEC-390 L1 H2 amend-stop-price path; conditional on H2 selection |
| RSK-DEC-390-CANCEL-AWAIT-LATENCY | MEDIUM | AMD-2 superseded by AMD-2-prime on cancel-and-await branch; conditional on H1/H4 selection |
| RSK-DEC-390-FINGERPRINT | MEDIUM | `_is_locate_rejection()` substring fingerprint depends on IBKR error string |
| RSK-CEILING-FALSE-POSITIVE | MEDIUM | DEC-390 L3 ceiling two-counter reservation pattern edge cases |
| RSK-RECONSTRUCTED-POSITION-DEGRADATION | MEDIUM-HIGH | `is_reconstructed = True` refusal posture; bounded by Sprint 31.94 D3; Sprint Abort Condition #7 trigger lowered to 2 weeks per H-R2-3 |

**2 NEW from Phase A Tier 3:**

| RSK | Severity | Description |
|-----|----------|-------------|
| RSK-FAI-COMPLETENESS | MEDIUM | FAI's self-falsifiability clause triggered; Round 3 may surface a fourth |
| RSK-CROSS-LAYER-INCOMPLETENESS | MEDIUM | Cross-layer composition test count at 5 (above floor; below exhaustive); CL-6 deferred per Decision 5 |

**Plus:**

| RSK | Severity | Description |
|-----|----------|-------------|
| RSK-SUPPRESSION-LEAK | LOW | `OrderManager._locate_suppressed_until` dict accumulates entries; partially-mitigated by AC2.5 broker-verification + Branch 4 |

### Process-evolution lessons (sprint-close materialization)

| Lesson | Date | Topic |
|--------|------|-------|
| F.5 | Sprint 31.91 (reaffirmed Sprint 31.92) | Structural-closure framing, NOT aggregate percentage claims (token-level: "comprehensive," "complete," "fully closed," "covers ~N%") |
| F.6 | 2026-04-29 (Sprint 31.92 Phase A Tier 3) | FAI completeness pattern — primitive-semantics assumptions whose violation silently produces the symptom class the proposed fix claimed to address |
| F.7 | 2026-04-29 (Sprint 31.92 Phase B re-run) | CL-6 deferral rationale — bounded session count vs. exhaustive coverage trade-off |

All three materialize at Sprint 31.92 sprint-close (D14 doc-sync) into
`docs/process-evolution.md`.

### Decision 7 verbatim location

`escalation-criteria.md` § "Round 3 Outcome Pre-Commitment (Operator-Bound)"
(lines 31–55). Reproduced verbatim in § 1 of this package above.

### Phase A Tier 3 verdict location

`tier-3-review-1-verdict.md` — full verdict (REVISE_PLAN, 2026-04-29).
Sub-area A finding (FAI entry #9 missing) drove REVISE_PLAN. Sub-areas
B–E provided sub-findings A14 / borderline / measured-only escalation /
Round 2 disposition re-validation / cross-layer / procedural deviations.

### Companion artifacts (Phase C set, sealed at end of prior session)

| # | Artifact | Path |
|---|----------|------|
| 1 | Design Summary (Phase B re-run) | `design-summary.md` |
| 2 | (Reserved) | — |
| 3 | Sprint Spec (Phase C revised) | `sprint-spec.md` |
| 4 | Spec by Contradiction (Phase C revised) | `spec-by-contradiction.md` |
| 5 | Session Breakdown (Phase C revised — 13 sessions) | `session-breakdown.md` |
| 6 | Regression Checklist (Phase C revised — 27 invariants) | `regression-checklist.md` |
| 7 | Escalation Criteria (Phase C revised — Decision 7 verbatim) | `escalation-criteria.md` |
| 8 | Doc Update Checklist (Phase C revised — sealed) | `doc-update-checklist.md` |
| 9 | **Adversarial Review Input Package — Round 3 (this artifact)** | `adversarial-review-input-package-round-3.md` |

Plus reference artifacts:

| Artifact | Path |
|----------|------|
| Falsifiable Assumption Inventory (Phase C revised — 9 entries) | `falsifiable-assumption-inventory.md` |
| Phase A Re-Entry Findings (Phase C revised) | `phase-a-reentry-findings.md` |
| Round 1 Revision Rationale | `revision-rationale.md` |
| Round 2 Disposition | `round-2-disposition.md` |
| Phase A Tier 3 Verdict #1 | `tier-3-review-1-verdict.md` |

### Repository

`https://github.com/stevengizzi/argus.git` (public). Sprint 31.91 sealed
at HEAD as of 2026-04-28; Sprint 31.92 has not landed yet. Round 3
reviewer reads `docs/architecture.md` §3.3 / §3.7 / §13 + `docs/decision-log.md`
DEC-117 / DEC-369 / DEC-372 / DEC-385 / DEC-386 / DEC-388 from HEAD as
the pre-change architectural anchor.

---

## End of package

**Phase C is SEALED.** Artifact 9 of 9 complete. Round 3 review is
unblocked.

**Operator next steps:**

1. Open a fresh Claude.ai conversation for Round 3 adversarial review.
2. Upload this package + the revised `sprint-spec.md` + `spec-by-contradiction.md`
   as the binding inputs.
3. Open with the Round 1+ reviewer-prompt from
   `protocols/adversarial-review.md` v1.1.0:

   > "I need you to adversarially review this REVISED sprint spec. This
   > is Round 3 — Round 1 and Round 2 produced [list of findings]
   > dispositioned per `revision-rationale.md` and `round-2-disposition.md`;
   > Phase A Tier 3 produced REVISE_PLAN per `tier-3-review-1-verdict.md`.
   > Your job is FULL SCOPE per Outcome C: find problems that the
   > revisions INTRODUCED OR FAILED TO FULLY ADDRESS, AND any new
   > primitive-semantics assumptions load-bearing on the proposed
   > mechanism that are NOT in the FAI's 9 entries. Try to break the
   > revised design. Find the flaws."

4. Reviewer produces a verdict per § 9 verdict template above.
5. Operator dispositions per Decision 7:
   - (a) primitive-semantics-class Critical → Phase A re-entry per
     Outcome C (4th revision pass).
   - (b) any other Critical class → RSK + ship to Phase D.
   - Outcome A (Round CLEAR) → ship to Phase D directly.

After Round 3 verdict + disposition, sprint planner proceeds to Phase D
(implementation prompt generation for S1a / S1b / S2a / S2b / S3a / S3b /
S4a-i / S4a-ii / S4b / S5a / S5b / S5c). The mid-sprint Tier 3 review
(M-R2-5) inserts between S4a-ii and S4b per Round 2 M-R2-5 disposition.
