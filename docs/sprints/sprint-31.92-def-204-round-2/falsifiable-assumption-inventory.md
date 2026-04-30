# Sprint 31.92 — Falsifiable Assumption Inventory (revised)

> **Phase A re-entry artifact (revised at Phase C 2026-04-29).** Authored per
> `protocols/sprint-planning.md` v1.3.0 step 9 (2026-04-29 amendment). This
> document IS the canonical FAI for Sprint 31.92; it is reproduced verbatim
> as the `## Falsifiable Assumption Inventory` section of the revised
> `sprint-spec.md` at Phase C.
>
> **Revision lineage:**
> - Round 1 (2026-04-28): inventory not yet authored; meta-pattern surfaced.
> - Round 2 (2026-04-29): inventory not yet authored; meta-pattern reaffirmed.
> - **Phase A re-entry (2026-04-29):** initial 8-entry inventory authored;
>   entries #3 + #5 flagged as ESCALATION (measured-only); entry #8 surfaced
>   as new finding.
> - **Phase A Tier 3 review #1 (2026-04-29):** verdict REVISE_PLAN. Tier 3
>   item A added entry #9 (callback-path bookkeeping atomicity); Tier 3 item
>   B extended H-R2-1's structural protection scope to all bookkeeping
>   callback paths. Sub-area B (FAI #5) recommended N≥100 (was N≥30).
>   Sub-area B (FAI #8) recommended option (a) over (b).
> - **Phase B re-run (2026-04-29):** 7 settled operator decisions adopted
>   verbatim. Decision 1 (FAI #3 adversarial sub-spike — worst-axis Wilson
>   UB), Decision 2 (FAI #5 N=100 hard gate), Decision 3 (FAI #8 option (a)
>   — 3 reflective-call sub-tests), Decision 5 (5 cross-layer composition
>   tests + `SimulatedBrokerWithRefreshTimeout` fixture per Tier 3 item E).
> - **This Phase C revision (2026-04-29):** materializes entry #9 + #2/#5/#8
>   status text updates + Net session-breakdown impact subsection re-derived
>   for the 13-session post-mitigation breakdown.
>
> **Origin (preserved verbatim from Phase A re-entry):** Round 1 caught the
> asyncio yield-gap race (a primitive-semantics assumption — the implicit
> claim that asyncio's single-threaded event loop serialized concurrent
> emit-side calls). Round 2 caught the `ib_async` position-cache freshness
> assumption (the implicit claim that `broker.get_positions()` returned
> fresh broker state). Phase A Tier 3 caught the callback-path bookkeeping
> atomicity assumption (the implicit claim that the H-R2-1 atomic-reserve
> protection was sufficient to guarantee L3 ceiling correctness). All three
> are primitive-semantics assumptions whose violation silently produced the
> symptom class the proposed fix claimed to address. Per
> `protocols/adversarial-review.md` v1.1.0 § Outcome C, the recurrence of
> the same primitive-semantics class across consecutive rounds returns the
> sprint to Phase A; this inventory is the structural defense.
>
> **Inventory falsifiability (preserved load-bearing clause):** Per
> `templates/sprint-spec.md` v1.2.0 § Falsifiable Assumption Inventory,
> this inventory is itself a falsifiable artifact. If Round 3 (or any
> subsequent review) finds an additional primitive-semantics assumption
> load-bearing on the proposed mechanism not in this list, the inventory
> has failed — and the mechanism's adversarial-review verdict must be
> downgraded accordingly. Phase A Tier 3 already exercised this clause
> once (entry #9 added); Round 3 full-scope cross-check is the next
> defense layer.

---

## Inventory (9 entries)

| # | Primitive-semantics assumption | Falsifying spike or test | Status |
|---|--------------------------------|--------------------------|--------|
| 1 | asyncio guarantees that synchronous Python statements between two `await` points (or in a coroutine body without any `await`) execute atomically with respect to other coroutines on the same event loop. The C-1 reservation pattern's correctness depends on `_reserve_pending_or_fail`'s body remaining synchronous post-refactor (no `await` between ceiling-check and reserve increment). **NOTE:** entry #9 extends this assumption to all callback paths that mutate the bookkeeping counters; entry #1 covers the place-time emit path specifically. | (a) **AST-level scan** in regression suite asserts no `ast.Await` node within `_reserve_pending_or_fail`'s body — `ast.parse(textwrap.dedent(inspect.getsource(om._reserve_pending_or_fail)))` walked for `ast.Await`; assertion fails on any await. (b) **Mocked-await injection test:** monkey-patch the implementation to insert `await asyncio.sleep(0)` between check and reserve, then assert the race IS observable under injection. The injection test is mechanism-sensitive: if the test still refuses the second coroutine even with the injection, the protection is verifying outcome only and the test is unsound. | **unverified — falsifying spike scheduled in S4a-i.** Will become **falsified** on first green S4a-i regression run. |
| 2 | `ib_async`'s position cache catches up to broker state within `Broker.refresh_positions(timeout_seconds=5.0)` under all observed reconnect-window conditions. AC2.5's refresh-then-verify mechanism's correctness depends on this. **High-volume steady-state behavior under hundreds of variants is explicitly out of Sprint 31.92 scope per Tier 3 item D / Decision 5 / DEF-FAI-2-SCOPE — deferred to Sprint 31.94 reconnect-recovery.** | **S3b sub-spike** (per C-R2-1 disposition): simulate Gateway disconnect/reconnect during paper hours; measure `cache_staleness_p95_ms`, `cache_staleness_max_ms`, `refresh_success_rate`, `refresh_p95_ms` across N≥10 disconnect/reconnect cycles. **Halt-or-proceed gate:** if `cache_staleness_max_ms > refresh_timeout_seconds × 1000` in any trial, the chosen fix is itself unreliable; halt and surface to operator. **Branch 4** (`verification_stale: true` alert) is the structural defense if measurement reveals non-convergent cases — preserves safety even when the spike falsifies. **`SimulatedBrokerWithRefreshTimeout` fixture (S5c) enables in-process Branch 4 unit testing; without the fixture Branch 4 is unreachable in `SimulatedBroker` per Tier 3 #B2 / Decision 5 / DEF-SIM-BROKER-TIMEOUT-FIXTURE.** | **unverified — falsifying spike scheduled in S3b; Branch 4 fallback + `SimulatedBrokerWithRefreshTimeout` fixture (S5c) are load-bearing defenses.** Status flips to **falsified** on first green S3b paper spike + green S5c CL-3 + green Branch 4 unit test. |
| 3 | IBKR's `modifyOrder` rejection rate is stable at ≤5% **on the production-reachable steady-state axis** (axis (i) concurrent amends across N≥3 positions). The H2 mechanism selection binds on this axis only. **Per Tier 3 Review #2 (2026-04-30) DEC-390 amended rule (loose reading):** axis (i) is binding; axes (ii) reconnect-window and (iv) joint reconnect+concurrent are RETAINED as **informational** characterization of H2 fail-loud behavior during Gateway disconnect (input to Sprint 31.94 reconnect-recovery design per DEF-241 / RSK-DEC390-31.94-COUPLING); axis (iii) stale-ID is DELETED entirely (state unreachable in production per DEC-117 + DEC-386 invariants; broker-correct rejection of modifications against cancelled orders is *desired* behavior — not a rejection-rate signal). The strict reading ("ALL four axes must remain ≤5% UB") was structurally degenerate (would have disqualified H2/H4/H1 simultaneously by design); the loose reading recovers the engineering question. Cross-reference: spec-by-contradiction.md §Out-of-Scope item 27. | **S1a (v2) adversarial sub-spike (per DEC-390 amended rule).** S1a v2 script: (a) axis (i) concurrent amends across N≥3 positions BINDS the H2/H4/H1 selection — JSON `binding_axis_result.concurrent_amends.wilson_upper_bound_pct` (renamed from `worst_axis_wilson_ub` to `axis_i_wilson_ub`); (b) axes (ii) reconnect-window and (iv) joint reconnect+concurrent reported under JSON `informational_axes_results` with Cat B.3 `instrumentation_warning` tag if Gateway-connection sampling reveals operator skipped manual disconnect (DEF-238); (c) axis (iii) stale-ID DELETED from spike — `_axis_stale_id()` removed; key absent from JSON output. **Halt-or-proceed gate uses `axis_i_wilson_ub`** only (NOT max across axes). | **unverified — falsifying spike scheduled in S1a v2 (post-DEC-390 re-run).** Will become **falsified** on green S1a v2 run if `axis_i_wilson_ub` satisfies the H2 < 5% / H4 5–20% / H1 ≥20% selection rule per Hypothesis Prescription. |
| 4 | The S1b substring fingerprint catches every variant of the locate-rejection error string IBKR can produce. AC2.1's case-B detection's correctness depends on this. | S1b substring-fingerprint validation across ≥5 symbols × ≥10 trials in the paper-account configuration; halts if observed strings disagree. Sampling is bounded to a single account, single Gateway version, single configuration. | **measured-only** — sampling within configuration only. Truly falsifying would require cross-version / cross-config sampling, which is out of scope for paper-trading validation. **Acceptable as measured-only because** the M-R2-1 case-A watchdog (AC2.7 `_pending_sell_age_seconds`) is **auto-activated** on first observed case-A in production paper trading per Decision 4 (`config/order_manager.yaml: pending_sell_age_watchdog_enabled: auto` flips to `enabled` on first `case_a_in_production` event; NOT manual operator activation). The watchdog provides the structural fallback for any unmodeled string variant. |
| 5 | `cancel_all_orders(symbol, await_propagation=True)` synchronously confirms all bracket-child cancellations broker-side before returning. The H1 fallback path's correctness depends on this — without broker-side confirmation, the post-cancel SELL emission can collide with still-active bracket children (OCA conflict; locate suppression; or worse, both). | **S1a strengthened cancel-then-immediate-SELL stress (per Decision 2 / DEF-FAI-N-INCREASE — N=30 → N=100).** S1a script: (a) issue `cancel_all_orders(symbol, await_propagation=True)`; (b) immediately attempt SELL emission (`reqId+1` SELL within ≤10ms of the cancel return); (c) verify across **N=100 trials** that no bracket-child OCA conflict, locate suppression, or position state inconsistency surfaces. **HARD GATE: if even 1 trial in 100 exhibits a conflict, H1 is NOT eligible regardless of `modifyOrder` Wilson UB.** This is a hard gate, not advisory. JSON output schema includes `h1_propagation_n_trials=100` and `h1_propagation_zero_conflict_in_100: bool`. This sub-spike is also the structural defense for the H-R2-2 H1-fallback-locate-reject branch — if H1 is unsafe under cancellation-not-yet-propagated conditions, the composite failure mode is worse than what H-R2-2 currently models. | **unverified — falsifying spike scheduled in S1a.** Will become **falsified** on green S1a run if `h1_propagation_zero_conflict_in_100 == true`. Hard-gated; any non-zero conflict count rules H1 out regardless of other measurements. |
| 6 | IBKR raises a locate-rejection exception (case B) on hard-to-borrow symbols rather than silently holding the order pending borrow (case A). AC2.1's exception-handler-based detection depends on this. | **S1b explicit case-A vs case-B differentiation** (per M-R2-1 disposition): output JSON includes `case_a_observed: bool`, `case_a_count: int`, `case_b_count: int`, `case_a_max_age_seconds: int`. The spike actively probes for case A — the breaking condition for the assumption — by submitting hard-to-borrow orders and watching for the order accepted-but-held outcome. **Conditional defense:** if case A is observed, AC2.7 `_pending_sell_age_seconds` watchdog activates immediately. **Decision 4 strengthening:** even if S1b does NOT observe case A, the watchdog is `auto`-mode and flips to `enabled` on first observed `case_a_in_production` event. | **unverified — falsifying spike scheduled in S1b.** The spike is genuinely falsifying (probes for the breaking condition); status flips to **falsified** on S1b green run regardless of which case is observed (because the spike output is itself the falsification record). |
| 7 | `on_position_closed` event fires on all four ARGUS position-close paths: (a) broker confirms zero shares; (b) `_flatten_pending` clears; (c) `ManagedPosition` removed from active-positions dict; (d) the canonical `on_position_closed` close-path itself. AC2.6's suppression-dict-clear mechanism's correctness depends on this. | **M-R2-2 regression test** exercises all four close paths and asserts the dict entry is cleared in each (`test_suppression_dict_cleared_on_all_position_close_paths`). If any path fails, S3b audit-and-fix-or-document: either the event must fire from all paths, OR the dict-clear logic subscribes to multiple events. | **unverified — falsifying spike scheduled in S3b.** Will become **falsified** on first green S3b regression run; if any close path fails the test, the disposition's "audit-and-fix-or-document" gate forces resolution before merge. |
| 8 | The H-R2-5 codebase scan for `is_stop_replacement=True` callers (Regression Checklist invariant 24) has no false-negative paths via reflective or aliased call patterns. The is-stop-replacement-only-from-`_resubmit_stop_with_retry`-normal-retry-path contract's enforcement depends on this. | **S4a-ii adversarial regression sub-tests (per Decision 3 / DEF-FAI-8-OPTION-A — option (a) chosen over (b)).** S4a-ii adds 3 reflective-call sub-tests probing whether the AST-level scan for `is_stop_replacement=True` callers catches: (a) `kw = {"is_stop_replacement": True}; om._check_sell_ceiling(..., **kw)` (`**kw` unpacking); (b) `flag = True; om._check_sell_ceiling(..., is_stop_replacement=flag)` (computed-value flag assignment); (c) `getattr(om, "_check_sell_ceiling")(..., is_stop_replacement=True)` (`getattr` reflective access). Each sub-test exercises the AST scanner against the reflective construct and asserts either detection-with-flag (preferred) or known-coverage-gap-documented (fallback). | **unverified — falsifying spike scheduled in S4a-ii.** Will become **falsified** on first green S4a-ii regression run. Option (b) accept-and-document **NOT TAKEN** per Decision 3. |
| 9 | **(NEW per Tier 3 item A — callback-path bookkeeping atomicity.)** All bookkeeping update paths on `cumulative_pending_sell_shares` and `cumulative_sold_shares` (place-side increment, cancel/reject decrement, partial-fill transfer, full-fill transfer, `_check_sell_ceiling` multi-attribute read) execute synchronously between bookkeeping read and write across the entire transition. The L3 ceiling correctness depends on the asyncio single-event-loop guarantee applying to **every path that mutates these counters, not only `_reserve_pending_or_fail`**. The `_check_sell_ceiling` check reads two attributes (`pending`, `sold`) and adds `requested`; if a callback path (e.g., `on_fill` processing a partial fill) yields between `pending -= filled_qty` and `sold += filled_qty`, another coroutine's ceiling check sees `pending` already decremented but `sold` not yet incremented — total is artificially low — and a SELL that should be blocked passes. This is exactly the structural class entry #1 exists to prevent, but entry #1's AST guard + mocked-await injection test are scoped narrowly to `_reserve_pending_or_fail`. | **S4a-ii AST-no-await scan + mocked-await injection regression extended to all callback paths that mutate the bookkeeping counters** (per Tier 3 items A + B / DEF-FAI-CALLBACK-ATOMICITY): `on_fill` (partial-fill transfer + full-fill transfer), `on_cancel` (decrement), `on_reject` (decrement), `_on_order_status` (status-driven mutations), and the `_check_sell_ceiling` multi-attribute read. Pattern-matches the entry #1 falsifying mechanism, applied across all 5 paths. The H-R2-1 disposition extension means the atomic-reserve protection is the **reference pattern**, and the same guard + injection test apply to every bookkeeping path. | **unverified — falsifying spike scheduled in S4a-ii.** Will become **falsified** on first green S4a-ii regression run. **Sprint-gating Round 3 advancement** per Tier 3 verdict — Round 3 reviewer's FAI cross-check explicitly confirms entry #9 + extended H-R2-1 protection. |

---

## Justification log for measured-only / unverified entries

The new template requires explicit per-entry justification when an entry is
**measured-only** or **unverified-without-falsifying-spike**. The recommended
Phase A actions are now SETTLED operator decisions; restated compactly here
for adversarial-review scrutiny:

- **#1 (asyncio synchronicity, narrow scope):** unverified at Phase C is
  normal — the falsifying mechanism is a regression test landing in S4a-i.
  No additional justification needed beyond "scheduled in session breakdown."

- **#2 (ib_async cache freshness):** unverified at Phase C; falsifying spike
  scheduled in S3b. Defense-in-depth via Branch 4 fallback + C-R2-1↔H-R2-2
  coupling (`halt_entry_until_operator_ack=True` if H1 active AND refresh
  fails) per Tier 3 item C. **`SimulatedBrokerWithRefreshTimeout` fixture
  (S5c) enables in-process Branch 4 unit testing per Tier 3 item E /
  Decision 5 / DEF-SIM-BROKER-TIMEOUT-FIXTURE.** **High-volume steady-state
  axis (DEF-FAI-2-SCOPE) explicitly out of Sprint 31.92 scope per Tier 3
  item D — deferred to Sprint 31.94 reconnect-recovery; FAI #2 scope-text
  amendment lands there.**

- **#3 (modifyOrder determinism):** unverified at Phase C; falsifying spike
  (axis (i) production-reachable steady-state) scheduled in S1a v2 per
  Tier 3 Review #2 verdict 2026-04-30 / DEC-390 amended rule. **`axis_i_wilson_ub`**
  drives halt-or-proceed gate per Hypothesis Prescription (axes (ii) and
  (iv) demoted to informational; axis (iii) deleted). Operator chose
  to add the adversarial sub-spike rather than retain measured-only with
  RSK-S1A-ADVERSARIAL-UNTESTED MEDIUM-HIGH (the latter would have been a
  Round 3 re-litigation candidate). Cross-reference: spec-by-contradiction.md
  §Out-of-Scope item 27; sprint-spec.md §Hypothesis Prescription amended
  halt-or-proceed gate language; RSK-VERDICT-VS-FAI-3-COMPATIBILITY
  (`docs/risk-register.md`).

- **#4 (locate-rejection string stability):** measured-only acceptable
  because **Decision 4** auto-activates the AC2.7 watchdog on first observed
  case-A in production paper trading (NOT manual operator activation). The
  watchdog is the structural fallback for any unmodeled string variant.
  Justification: "Cross-version / cross-config sampling is operationally
  infeasible for paper validation; auto-activating watchdog provides the
  structural fallback for any unmodeled string variant."

- **#5 (await_propagation atomicity):** unverified at Phase C; falsifying
  spike (cancel-then-immediate-SELL stress at N=100) scheduled in S1a per
  Decision 2. **Hard gate:** any conflict in 100 trials → H1 NOT eligible
  regardless of `modifyOrder` Wilson UB. N increased from ≥30 to N=100 per
  Tier 3 sub-area B finding (Wilson UB on 0/30 is roughly [0%, 11.6%] —
  all-30-green still permits ~1-in-9 production failures; N=100 tightens
  the bound).

- **#6 (locate-rejection exception vs held order):** unverified at Phase C;
  falsifying spike actively probes for the breaking condition. Strong
  falsifiability — no escalation. Decision 4 watchdog auto-activation is
  the additional structural defense.

- **#7 (on_position_closed completeness):** unverified at Phase C;
  falsifying regression scheduled in S3b. Strong falsifiability — no
  escalation.

- **#8 (AST callsite scan completeness):** unverified at Phase C;
  falsifying mechanism scheduled in S4a-ii per Decision 3 (option (a)
  adversarial regression sub-tests over option (b) accept-and-document).
  Tier 3 sub-area B finding: "the static analysis IS the load-bearing
  defense for invariant 24; accepting a known-coverage-gap weakens that
  defense." Cost (3 test cases) is acceptable; value (closing the
  falsification surface) is high.

- **#9 (callback-path bookkeeping atomicity, NEW):** unverified at Phase C;
  falsifying mechanism scheduled in S4a-ii per Tier 3 items A + B. The
  asyncio-single-event-loop guarantee must apply to every path that mutates
  `cumulative_pending_sell_shares` or `cumulative_sold_shares`, not only
  `_reserve_pending_or_fail`. **Sprint-gating Round 3 advancement** —
  Round 3 reviewer's FAI cross-check explicitly confirms entry #9 +
  extended H-R2-1 protection.

---

## Summary table for Phase B/C handoff

| # | Status | Phase A/B/C action | Session-breakdown impact |
|---|--------|----------------------|--------------------------|
| 1 | unverified (falsifying scheduled) | — | S4a-i delivers AST guard + mocked-await injection regression |
| 2 | unverified (falsifying scheduled) + Branch 4 + Tier 3 item C coupling + S5c fixture | — | S3b delivers spike + AC2.5 + Branch 4; S5c delivers `SimulatedBrokerWithRefreshTimeout` fixture + CL-3 |
| **3** | **unverified (falsifying scheduled per Decision 1)** | adversarial sub-spike landed in S1a | S1a script extended (~280 LOC; was ~180 LOC); JSON schema gains `adversarial_axes_results`, `worst_axis_wilson_ub` |
| 4 | measured-only (acceptable with Decision 4 auto-activation) | watchdog auto-activates per Decision 4 | S3a adds `pending_sell_age_watchdog_enabled` config field with `auto`/`enabled`/`disabled`; S4a-i implements auto-flip on first `case_a_in_production` event |
| **5** | **unverified (falsifying scheduled per Decision 2)** | strengthened cancel-then-SELL stress at N=100 hard gate | S1a script extended; JSON schema gains `h1_propagation_n_trials=100`, `h1_propagation_zero_conflict_in_100: bool` |
| 6 | unverified (falsifying scheduled) | — | S1b delivers spike with `case_a_observed`, `case_a_count`, `case_b_count`, `case_a_max_age_seconds` |
| 7 | unverified (falsifying scheduled) | — | S3b delivers regression test for all 4 close paths |
| **8** | **unverified (falsifying scheduled per Decision 3 — option (a))** | 3 reflective-call sub-tests in S4a-ii | S4a-ii adds 3 sub-tests probing `**kw` unpacking, computed-value flag, `getattr` reflective access |
| **9** | **unverified (NEW per Tier 3 item A; falsifying scheduled per Tier 3 item B)** | AST-no-await scan + mocked-await injection extended to all bookkeeping callback paths | S4a-ii (NEW SESSION) delivers regression infrastructure on `_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, `_check_sell_ceiling` multi-attribute read |

**Net session-breakdown impact (Phase B re-run, post-Tier-3, 13 sessions):**

- **S1a score impact:** entries 3 + 5 strengthen the existing spike script (~280 LOC, was ~180 LOC; new measurement modes; new JSON schema fields). Single-file change; compaction score unchanged at Medium 12.
- **S3a score impact:** new `pending_sell_age_watchdog_enabled` config field per Decision 4. +1 modified file is bundled with the existing config-additions session; compaction score unchanged at Medium 13.
- **S3b score impact:** entry 2 + Tier 3 item C coupling + Branch 4 (~AC2.5 three-branch + Branch 4 + halt-entry-until-operator-ack threading). +1 logical test over Round-1-revised; compaction score 13 post-mitigation (2 of 10 logical tests deferred to S5b composite).
- **S4a-i score impact:** entry 1 (existing AST guard + mocked-await injection landed in this session, scope unchanged) + 5 emit-site guards + reservation pattern + reconstructed-position refusal + AC2.7 auto-activation per Decision 4. Compaction score Medium 13.5 post-mitigation (option δ — 3 pre-flight reads, 7 effective tests; 2 logical tests deferred to S5b composite).
- **S4a-ii (NEW SESSION) score impact:** entries 8 + 9 extend the AST-guard pattern to all bookkeeping callback paths and add 3 reflective-call sub-tests. **New file `tests/execution/order_manager/test_def204_callback_atomicity.py`** (~120 LOC, 7 tests). Compaction score Medium 9.5 (1 file +2; 0–1 modified +0–1; 4 reads +4; 7 tests +3.5).
- **Mid-Sprint Tier 3 (M-R2-5) inserted between S4a-ii and S4b:** unchanged from Round-2 disposition; this is distinct from the Phase A Tier 3 already conducted.
- **S5c (NEW SESSION) score impact:** Tier 3 item E / Decision 5 — 5 cross-layer composition tests (CL-1 through CL-5) + `SimulatedBrokerWithRefreshTimeout` fixture (DEF-SIM-BROKER-TIMEOUT-FIXTURE). **New file `tests/integration/conftest_refresh_timeout.py`** (~80 LOC). Compaction score Medium 13 (1 fixture file +2; 1 modified +1; 4 reads +4; 6 tests +3; complex integration YES +3).

**Total cumulative diff bound on `argus/execution/order_manager.py`:**
recalibrated to **~1150–1300 LOC** (was ~1100–1200 LOC pre-Tier-3) per Tier
3 guidance, accommodating callback-path AST guards + Branch 4 coupling +
AC2.7 auto-activation + `halt_entry_until_operator_ack` field threading.

**Total session count:** **13 sessions** (was 10 pre-Tier-3): 2 spike +
8 implementation/validation + 2 NEW (S4a-ii + S5c) + 1 mid-sprint Tier 3
review event (M-R2-5). Zero sessions at compaction score 14+ post-mitigation.

**Net pytest target:** 88–114 new logical tests (was 75–95 pre-Phase-B-re-run);
~108–134 effective with parametrize multipliers. Final test-count target:
5,357–5,403 pytest (5,269 baseline + 88–134 new), 913 Vitest unchanged.

---

## Out of scope (deliberately not in this inventory)

For Round 3 reviewer reference. The following are **not** primitive-semantics
assumptions and are explicitly excluded from this inventory:

- **Operator-process assumptions** (e.g., "operator will see and acknowledge
  the alert" for H-R2-2 HALT-ENTRY; "operator will run daily-flatten script"
  for RSK-RECONSTRUCTED-POSITION-DEGRADATION). These are process risks tracked
  in the RSK list per Severity Calibration Rubric, not primitive-semantics.

- **System-design choices** (e.g., "stop-replacement bypassing the ceiling
  cannot itself produce over-flatten" for H-R2-5; "HALT-ENTRY rather than
  auto-recovery is the correct posture" for H-R2-2). These are design
  decisions tracked in DEC entries, not primitive-semantics.

- **Statistical-inference choices** (e.g., "Wilson UB at 95% confidence is the
  right asymmetric-conservative bound" for M-R2-4). These are methodological
  choices, not claims about primitive runtime behavior.

- **Architectural-closure assumptions for prior sprints** (e.g., DEC-386's
  4-layer OCA defense; DEC-388's 5-layer alert observability). These were
  validated/falsified within Sprint 31.91 and are not Sprint-31.92-load-bearing.
  However, **DEC-386 was empirically falsified on 2026-04-28 (60 NEW phantom
  shorts via cross-layer composition path);** Sprint 31.92 is the response.
  This inventory does not re-litigate DEC-386's per-layer assumptions but
  does include the ib_async cache primitive (#2) that the empirical
  falsification surfaced.

- **CL-6 cross-layer composition (rollback + locate-suppression interaction)**
  per Decision 5 — explicitly OUT of Sprint 31.92 scope; deferred with
  rationale documented in `docs/process-evolution.md`. CL-1 through CL-5
  cover the cross-layer compositions Tier 3 sub-area D considered
  operationally relevant.

---

## Round 3 reviewer protocol

Per `protocols/adversarial-review.md` v1.1.0 § Outcome C, Round 3 must be
**full scope, not narrowed.** Round 2 disposition's recommendation of
"narrowest possible scope" (line 454) is superseded by the 2026-04-29
amendment.

Round 3 reviewer's FAI-specific tasks:

1. **Completeness check.** Identify any primitive-semantics assumption
   load-bearing on the proposed mechanism that is NOT in this inventory.
   Per the inventory's self-falsifiability clause, any new finding indicates
   the inventory has failed. **Phase A Tier 3 already exercised this
   clause once (entry #9 added). Round 3 is the next layer.** A finding
   here routes per Decision 7 (a) — primitive-semantics-class Critical →
   another revision pass (Phase A re-entry per Outcome C).

2. **Status-rating audit.** For each entry rated **measured-only** or
   **unverified**, scrutinize the justification. The template reminds:
   *"measured-only spikes are the failure mode this section exists to
   prevent."* All three Round-2 ESCALATION FLAGS (entries 3, 5, 8) are now
   rated unverified-with-falsifying-spike-scheduled per the settled
   operator decisions; entry #4 remains measured-only with explicit
   Decision-4 auto-activation justification.

3. **Spike-quality check.** For each **unverified** entry with a scheduled
   falsifying spike, verify the spike actually falsifies (probes for
   breaking conditions) rather than measures (samples normal conditions).
   Specifically:
   - Entry #3: confirm S1a's adversarial axes (concurrent / reconnect /
     stale-ID amends) actually attempt to break the determinism claim.
   - Entry #5: confirm N=100 cancel-then-immediate-SELL stress with
     ≤10ms gap actually exercises the propagation-not-yet-converged
     condition.
   - Entry #8: confirm the 3 reflective-call sub-tests actually probe
     for AST-scan false-negative paths.
   - Entry #9: confirm the AST-no-await scan + mocked-await injection
     pattern is applied across ALL 5 callback paths (not just one) and
     that the multi-attribute read in `_check_sell_ceiling` is included.

4. **Cross-Layer Composition Test check.** Per
   `templates/sprint-spec.md` v1.2.0, DEC-391 claims architectural closure
   of 4 layers and therefore Sprint 31.92's regression checklist MUST
   include cross-layer composition tests (scenarios where the failure of
   one layer is supposed to be caught by another). **Sprint 31.92 commits
   to 5 tests (CL-1 through CL-5) per Decision 5 — above the template's
   "at least one" floor; above Tier 3's 3-test floor. CL-6 (rollback +
   locate-suppression interaction) is explicitly OUT of Sprint 31.92
   scope per Decision 5 with rationale in `docs/process-evolution.md`.**
   Round 3 reviewer should verify the regression-checklist revision
   includes all 5 tests AND that the `SimulatedBrokerWithRefreshTimeout`
   fixture (DEF-SIM-BROKER-TIMEOUT-FIXTURE) makes Branch 4 reachable
   in-process for CL-3.

**Round 3 escalation pre-commitment (Decision 7) is the binding contract
for what happens after Round 3 produces a Critical finding.** Reviewer is
referred to the revised `escalation-criteria.md` § Round 3 Outcome
Pre-Commitment for the verbatim text.

---

## Pending FAI extensions committed in `round-3-disposition.md`

**Operator-override audit-trail anchor per Round 3 disposition (Decision
7 (b) routing for C-R3-1).** The two FAI entries below are committed in
`round-3-disposition.md` § 6 with deferred materialization; the FAI
table above stays at 9 entries until S3b / S4a-ii sprint-close materialize
the new entries inline. This subsection makes the deferred materialization
auditable from this artifact directly (not just from the disposition).

### Pending FAI #10 — `Broker.refresh_positions()` concurrent-caller correlation (NEW per Round 3 C-R3-1)

**Materialization timing:** S3b sprint-close (per Decision 7 (b)
operator-override rationale; per `doc-update-checklist.md` D15).

**Text (verbatim from `round-3-disposition.md` § 6.1):**

> *FAI #10:* `Broker.refresh_positions()` synchronizes broker
> round-trip per-caller — concurrent callers each correctly correlate
> their `wait_for` return with their own `reqPositions()` invocation,
> OR the implementation explicitly serializes concurrent callers via
> single-flight pattern with coalesce window. The AC2.5
> broker-verification-at-timeout fallback's correctness depends on this.
>
> **Falsifying spike:** S3b sub-spike spawns N=20 coroutines calling
> `refresh_positions()` near-simultaneously (≤10ms separation) WITHOUT
> serialization mitigation; mocked-await injection between A's
> `reqPositions()` and B's `reqPositions()` with deterministic
> broker-state-change between; assert the race IS observable
> (stale-for-B classification). Then with the Fix A serialization
> mitigation enabled, assert the race is NOT observable. Cross-layer
> falsification at CL-7 in S5c.
>
> **Status:** unverified — falsifying spike scheduled in S3b. Will
> become falsified on green S3b spike + green CL-7. Sprint Abort
> Condition (NEW): if Fix A spike fails AND no alternative
> serialization design, sprint halts and operator decides whether to
> escalate to Phase A re-entry retroactively.

### Pending FAI #11 — Bookkeeping callsite-enumeration exhaustiveness (NEW per Round 3 H-R3-5)

**Materialization timing:** S4a-ii sprint-close (per
`doc-update-checklist.md` D16).

**Text (verbatim from `round-3-disposition.md` § 6.2):**

> *FAI #11:* All sites in `argus/execution/order_manager.py` that
> mutate `cumulative_pending_sell_shares` or `cumulative_sold_shares`
> are enumerated in the FAI #9 protected callsite list (`_reserve_pending_or_fail`,
> `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, plus
> `_check_sell_ceiling`'s multi-attribute read; plus `reconstruct_from_broker`
> for initialization). The L3 ceiling correctness depends on FAI #9's
> protection covering EVERY mutation site, not just the enumerated
> ones.
>
> **Falsifying spike:** S4a-ii regression test
> `test_bookkeeping_callsite_enumeration_exhaustive` — AST scan walks
> `OrderManager`'s source for `ast.AugAssign` nodes targeting
> `cumulative_pending_sell_shares` or `cumulative_sold_shares`; finds
> the enclosing function name for each; asserts the set of enclosing
> functions is a subset of the expected callsite list. Falsifies if a
> mutation site exists outside the expected list (e.g.,
> `_on_exec_details` if it exists in code).
>
> **Status:** unverified — falsifying spike scheduled in S4a-ii. Will
> become falsified on green S4a-ii regression run. Resolution if
> falsified: either add the discovered callsite to FAI #9's protection
> scope (preferred) or document the coverage gap with explicit
> rationale.
