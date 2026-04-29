# Sprint 31.92 — Phase A Re-Entry Findings (revised)

> **Phase A re-entry artifact (revised at Phase C 2026-04-29).** Companion
> to `falsifiable-assumption-inventory.md`. Re-validates each Round 2
> disposition against the new FAI; surfaces procedural concerns introduced
> by the 2026-04-29 metarepo amendments; proposes the revised Phase B →
> Phase C → Round 3 sequence.
>
> **Inputs:**
> - `round-2-disposition.md` (operator-confirmed; 14 dispositions)
> - `falsifiable-assumption-inventory.md` (Phase A authored 2026-04-29; 8
>   entries — revised at Phase C to 9 entries per Tier 3 item A)
> - `tier-3-review-1-verdict.md` (Phase A Tier 3 review #1, 2026-04-29,
>   verdict REVISE_PLAN)
> - `protocols/sprint-planning.md` v1.3.0
> - `protocols/adversarial-review.md` v1.1.0
> - `protocols/tier-3-review.md` v1.1.0
> - `templates/sprint-spec.md` v1.2.0
> - `templates/spec-by-contradiction.md` v1.1.0
>
> **Revision lineage:**
> - Phase A re-entry initial authoring (2026-04-29): 14 dispositions
>   re-validated; H-R2-1 marked "no addendum needed"; Substantive vs
>   Structural triggers fired 4 of 8.
> - **Phase A Tier 3 review #1 verdict (2026-04-29):** REVISE_PLAN. Sub-area
>   A finding: FAI entry #9 missing; H-R2-1 protection scope is narrower
>   than the L3 ceiling mechanism's correctness scope. Sub-area C explicit:
>   "H-R2-1 (atomic `_reserve_pending_or_fail`) — needs scope extension.
>   Findings document records 'no addendum needed.' Per Sub-area A finding
>   #9, the disposition's protection is narrower than the L3 ceiling
>   mechanism's correctness scope. Phase C must extend the AST-no-await
>   guard + mocked-await injection pattern to all bookkeeping callback
>   paths."
> - **This Phase C revision (2026-04-29):** materializes the H-R2-1
>   protection-scope-extension addendum per Tier 3 item B / Sub-area C;
>   updates Substantive vs Structural assessment to 5 of 8 triggers fired
>   (Trigger #2 re-counted: entry #9 NEW + #3/#5/#8 status promoted to
>   unverified-with-falsifying-spike-scheduled — single re-rating event
>   that fires both Trigger #2 sub-conditions). The remaining 13 disposition
>   re-validations stay as recorded.

---

## Summary

- **All 14 Round 2 dispositions re-validate** under the FAI. No disposition
  is invalidated. **Three dispositions required strengthening at Phase A
  re-entry** to align with the FAI's measured-only escalation flags:
  - C-R2-1 + S1a (entry #5): the cancel-then-immediate-SELL stress sub-spike.
  - H-R2-2 indirectly affected (entry #5 strengthening hard-gates H1 selection,
    which removes the H1-fallback-locate-reject branch from the table of
    routinely-reachable paths).
  - M-R2-1 (entry #4): strengthen the deferred-DEF filing to auto-activate
    AC2.7 watchdog on first observed case-A in production paper trading.
- **One new primitive-semantics assumption surfaced at Phase A re-entry**
  (entry #8 — AST callsite scan completeness for `is_stop_replacement=True`).
  H-R2-5 disposition needs a small extension.
- **Two ESCALATION FLAGS** in the FAI (entries #3 and #5) required Phase A
  action OR explicit operator sign-off. **Settled at Phase B re-run via
  Decisions 1 and 2.**
- **Procedural concerns:** the 2026-04-29 Outcome C protocol requires (a) a
  Phase A independent design review (Tier 3) and (b) Round 3 at full scope,
  not narrowed. Both are deviations from the Round 2 disposition's recommended
  plan. **Concern 1 (Round 3 full scope) and Concern 2 (Phase A Tier 3) both
  satisfied: Phase A Tier 3 review #1 conducted 2026-04-29.**
- **NEW from Phase A Tier 3 review #1 (2026-04-29):** FAI entry #9 added
  (callback-path bookkeeping atomicity, Tier 3 item A); H-R2-1 protection
  scope extended to all bookkeeping callback paths (Tier 3 item B / Sub-area
  C — the addendum below). FAI #5 N strengthened to 100 (Tier 3 sub-area B).
  FAI #8 option (a) chosen over (b) (Tier 3 sub-area B). Cross-layer test
  count committed to ≥4 (Decision 5: 5 tests, CL-1 through CL-5; CL-6
  explicitly out per Decision 5). C-R2-1 + H-R2-2 coupling materialized
  (Tier 3 item C — `halt_entry_until_operator_ack=True` if H1 active AND
  refresh fails).

---

## Per-disposition re-validation

### C-R2-1 — broker-verification + ib_async cache freshness — VALIDATES with addendum

**Maps to FAI entries:** #2 (ib_async cache freshness) — primary.

**Validation:** The disposition's `Broker.refresh_positions()` ABC method,
S3b sub-spike, and Branch 4 fallback collectively address FAI #2 with a
falsifying spike + structural defense. The fix shape holds.

**Addendum (relates to FAI #5 + Tier 3 item C):** The disposition's Branch
4 fallback fires a `phantom_short_retry_blocked` alert with
`verification_stale: true` when refresh fails. **Round 2 disposition does
not specify whether the H1 path is also reachable when verification is
stale.** If H1 is selected and the post-cancel SELL emission can't await
verification, the H-R2-2 composite failure mode compounds — H1's
"cancel-and-await" depends on FAI #5 (`await_propagation` atomicity), and
FAI #5's N=30 was statistically weak (Tier 3 sub-area B → N=100 per
Decision 2).

**Recommended addition to C-R2-1 for Phase C (MATERIALIZED at Phase C per
Tier 3 item C):** Add explicit clause to AC2.5 that if H1 is the active
mechanism AND `Broker.refresh_positions()` raises or times out, the
position is treated as `halt_entry_until_operator_ack=True` (consistent
with H-R2-2's HALT-ENTRY posture). This couples C-R2-1 and H-R2-2
explicitly, preventing the compound failure mode.

**Tier 3 item E addendum (NEW per 2026-04-29 verdict / Decision 5):**
`SimulatedBroker.refresh_positions()` is no-op or instant-success per
L-R2-3; in-process tests cannot exercise Branch 4. New
`SimulatedBrokerWithRefreshTimeout` fixture variant added at S5c
(DEF-SIM-BROKER-TIMEOUT-FIXTURE) — enables CL-3 cross-layer test AND a
dedicated Branch 4 unit test.

---

### H-R2-1 — synchronous-before-await ordering — VALIDATES with PROTECTION-SCOPE-EXTENSION addendum

**Maps to FAI entries:** #1 (asyncio synchronicity, narrow scope) — primary;
#9 (callback-path bookkeeping atomicity, broad scope) — extension.

**Validation:** The atomic `_reserve_pending_or_fail()` synchronous method +
AST-level guard + mocked-await injection test directly correspond to the FAI
#1 falsifying mechanism. The injection test is the load-bearing check that
the test is mechanism-sensitive. The fix shape holds at the place-time emit
path.

**Addendum (NEW per Phase A Tier 3 review #1 verdict, 2026-04-29 — Tier 3
item B / Sub-area C):** The original Phase A re-entry findings document
recorded "no addendum needed" for H-R2-1. **Phase A Tier 3 sub-area A's
falsification probe surfaced FAI entry #9 (callback-path bookkeeping
atomicity).** The L3 ceiling check reads two attributes (`pending`, `sold`)
and adds `requested`; if a callback path (e.g., `on_fill` processing a
partial fill) yields between `pending -= filled_qty` and `sold +=
filled_qty`, another coroutine's ceiling check sees `pending` already
decremented but `sold` not yet incremented — total is artificially low —
and a SELL that should be blocked passes. **The H-R2-1 disposition's
structural protection is therefore narrower than the L3 ceiling
mechanism's correctness scope.** The C-1 disposition's "AC3.1 enumerates
all 5 state transitions; AC3.5 race test validates concurrency safety"
enumerates transitions in prose, but the structural protection only covers
one of them. The other four paths rely on implementation discipline alone.

**Required revision (drives REVISE_PLAN per Tier 3 verdict):**

1. Add FAI entry #9 with the callback-path bookkeeping atomicity assumption
   text. **(Materialized at Phase C in revised
   `falsifiable-assumption-inventory.md`.)**
2. Falsifying mechanism: extend the AST-no-await scan + mocked-await
   injection pattern to all callback paths that mutate the bookkeeping
   counters: `on_fill` (partial-fill transfer + full-fill transfer),
   `on_cancel` (decrement), `on_reject` (decrement), `_on_order_status`
   (status-driven mutations), and the `_check_sell_ceiling` multi-attribute
   read. **(Materialized at Phase C in S4a-ii session, NEW per Tier 3
   verdict.)**
3. Add S4a-ii regression sub-test asserting the synchronous-update invariant
   on each callback path. **(Materialized as
   `tests/execution/order_manager/test_def204_callback_atomicity.py`,
   ~120 LOC, 7 tests.)**
4. H-R2-1 disposition extension: the atomic-reserve protection is the
   reference pattern; the same guard applies to all bookkeeping paths.
   **(Materialized at Phase C as AC3.1 + AC3.5 extended scope; regression
   invariant 23 NEW.)**

**Implementation lives in S4a-ii's regression-test infrastructure.**
Preferred outcome is zero production-code change in `argus/execution/order_manager.py`,
with the test file establishing the regression guard. If static analysis
reveals an existing await between bookkeeping read and write,
production-code amendment is allowed at S4a-ii under the same
synchronous-before-await contract.

---

### H-R2-2 — H1 last-resort + locate-suppression composite — VALIDATES with elevated severity + Tier-3 strengthening

**Maps to FAI entries:** #5 (await_propagation atomicity) — implicit
dependency.

**Validation:** The disposition's HALT-ENTRY posture, IMMEDIATE
`phantom_short_retry_blocked` alert, and operator-driven resolution are
correct given current understanding. **However, the FAI #5 escalation flag
elevates the severity of this disposition's underlying assumption.**

**Critical interaction with FAI #5 (preserved from Phase A re-entry
initial authoring):** Currently, S1a's `h1_propagation_converged` was a
measurement, not a hard gate. M-R2-4's Wilson UB rule chose H2 vs H4 vs H1
based on `modifyOrder` rejection rate. **There was no current gate that
prevented H1 from being selected even if `await_propagation`'s atomicity
failed under stress** — the H1 path could be selected (when modifyOrder
rejection rate is high), and the H1 fallback could itself be unsafe
(because cancel doesn't actually propagate before SELL emission).

**Recommended addition to H-R2-2 for Phase C (MATERIALIZED + STRENGTHENED
per Tier 3 sub-area B + Decision 2 — N=100, not N=30):** Extend the S1a
halt-or-proceed gate language to:

> "Compute Wilson UB from observed rejection rate AS WELL AS the
> cancel-then-immediate-SELL stress sub-spike outcomes. **Decision rule per
> Decision 2:** pick H2 if Wilson UB < 5% AND `h1_propagation_zero_conflict_in_100
> == true`; pick H4 if 5% ≤ Wilson UB < 20% AND
> `h1_propagation_zero_conflict_in_100 == true`; pick H1 ONLY IF
> `h1_propagation_zero_conflict_in_100 == true` AND Wilson UB ≥ 20% AND
> operator confirms H1 selection in writing per existing tightened gate
> language. **If even 1 trial in 100 exhibits a conflict, H1 is NOT eligible
> regardless of Wilson UB; surface to operator with explicit 'H1 unsafe'
> determination and require alternative architectural fix (likely Sprint
> 31.94 D3 or earlier).**"

This is a structural change to the Hypothesis Prescription's halt-or-proceed
gate (per Substantive vs Structural Rubric trigger #8) — Phase B must
re-run. **Confirmed by Phase A Tier 3 verdict (REVISE_PLAN); re-run
completed 2026-04-29.**

---

### H-R2-3 — RSK severity calibration — VALIDATES

**Maps to FAI entries:** None (process risk, not primitive-semantics).

**Validation:** RSK rated MEDIUM-HIGH per Severity Calibration Rubric (the
mitigation depends on operator action — daily-flatten — that empirically
failed within the last 10 sprints; mitigation depends on a sprint-bounded
fix and the bound exceeds 4 weeks if 31.93 + 31.94 each take 3 weeks). The
calibration aligns with the new template's MEDIUM-HIGH floor.

**No addendum needed.** The roadmap-level question (31.94 D3 prioritization)
remains flagged for separate operator decision per Decision 6 (Sprint scope:
CONTINUE 31.92, Option A; Sprint 31.94 D3 prioritization is NOT brought
forward; treated as a separate Discovery activity).

---

### H-R2-4 — startup CRITICAL warning — VALIDATES

**Maps to FAI entries:** None (process / CLI, not primitive-semantics).

**Validation:** The combined ntfy.sh + canonical-logger CRITICAL +
`--allow-rollback` flag fix is structurally sound. The flag transforms
accidental rollback into explicit operator action; the dual-channel
emission ensures audit trail and operator-attention coverage.

**No addendum needed.**

---

### H-R2-5 — `_resubmit_stop_with_retry` ceiling-vs-protective conflict — VALIDATES with addendum (now strengthened per Tier 3 sub-area B)

**Maps to FAI entries:** #8 (AST callsite scan completeness) — surfaced by
Phase A re-entry.

**Validation:** The `is_stop_replacement: bool` flag with stop-replacement
exemption + AST-level callsite scan + 5-callsite enumeration is sound. The
five caller sites are correctly enumerated.

**Addendum:** The AST-level callsite scan in Regression Checklist invariant
24 has potential false-negative paths via reflective access (`getattr`),
keyword-arg unpacking (`**kw`), and computed-value flag (`flag = True;
fn(..., is_stop_replacement=flag)`). Per FAI #8, Phase A action is one of:

- (a) **Add S4a regression sub-test** that intentionally introduces all three
  variants and asserts the AST scan catches them.
- (b) **Accept the limitation in writing** in the Regression Checklist text,
  raising invariant 24 from "guard" to "guard with a known coverage gap on
  reflective/aliased call patterns" with explicit operator sign-off.

**Original Phase A re-entry recommendation:** (b). Cost-benefit: catching
reflective access in static analysis requires a much heavier check
(whole-program or runtime tracing); the marginal value is low because all
current callers are static and named.

**Tier 3 sub-area B reversal (REVISE_PLAN):** "This Tier 3 prefers option
(a) — the static analysis IS the load-bearing defense for invariant 24;
accepting a known-coverage-gap weakens that defense. Cost is three test
cases; value is closing the falsification surface. Operator may override on
cost-benefit, but the floor recommendation is option (a)."

**Settled at Phase B re-run via Decision 3:** option (a) chosen. S4a-ii
adds 3 reflective-call sub-tests probing whether the AST-level scan for
`is_stop_replacement=True` callers catches (a) `**kw` unpacking, (b)
computed-value flag assignment, (c) `getattr` reflective access.

---

### M-R2-1 — held-order semantics case A vs B — VALIDATES with addendum (now strengthened per Decision 4)

**Maps to FAI entries:** #4 (locate-rejection string stability), #6
(locate-rejection exception vs held order).

**Validation:** S1b's case-A vs case-B differentiation directly addresses FAI
#6. Conditional AC2.7 watchdog is the right structural defense.

**Addendum (relates to FAI #4):** The disposition currently activates AC2.7
ONLY IF case A is observed in S1b. **If S1b's 5×10 sample doesn't observe
case A but case A surfaces in production paper trading**, the system has no
defense until manual investigation triggers a sprint amendment. Per FAI #4's
recommended Phase A action:

**Recommended addition to M-R2-1 for Phase C (MATERIALIZED per Decision 4):**
Strengthen the deferred-DEF filing to include automatic activation of AC2.7
watchdog on first observed case A in production paper trading. The
activation is implemented as a config toggle
(`config/order_management.yaml: pending_sell_age_watchdog_enabled: auto`)
with `auto` mode flipping to `enabled` on first observed
`case_a_in_production` event. This converts FAI #4 from
measured-only-acceptable to measured-only-with-auto-activating-defense.

**NOT manual operator activation per Decision 4.** The watchdog provides
the structural fallback for any unmodeled locate-rejection string variant.

---

### M-R2-2 — `on_position_closed` event coverage — VALIDATES

**Maps to FAI entries:** #7 (on_position_closed completeness).

**Validation:** Regression test exercising all four close paths is the
falsifying mechanism for FAI #7. The fix shape is correct.

**No addendum needed.**

---

### M-R2-3 — A13 freshness check semantics — VALIDATES

**Maps to FAI entries:** None (data validation, not primitive-semantics).

**Validation:** Both mtime AND content checks are required; A13 fires on
either failure. The C9 item 10 "≥7 consecutive daily green runs"
clarification that operator must verify content-green AND mtime-green is
correct.

**No addendum needed.**

---

### M-R2-4 — S1a 50-trial Wilson UB — VALIDATES with addendum (now strengthened per Decision 1)

**Maps to FAI entries:** #3 (modifyOrder determinism) — directly relevant.

**Validation as Round 2 disposition specifies:** Wilson UB rule provides
asymmetric-conservative statistical safety net. The fix shape addresses the
sampling-uncertainty axis of the determinism assumption.

**Addendum (per FAI #3 ESCALATION FLAG):** Wilson UB does NOT address
adversarial conditions (concurrent amends, reconnect-window amends, stale-ID
amends). Per FAI #3's recommended Phase A action:

**Recommended addition to M-R2-4 for Phase C (MATERIALIZED per Decision 1):**
Add an S1a adversarial sub-spike (extended in `s1a-spike-path1` script) that
exercises (i) concurrent amends across N≥3 positions, (ii) amends during a
Gateway reconnect window, (iii) amends with intentionally stale order IDs.
Each adversarial axis produces its own rejection-rate distribution;
halt-or-proceed gate uses the **worst** axis's Wilson UB, not the
steady-state UB.

This is a structural change to S1a's session scope (Substantive vs Structural
Rubric trigger #6 — adds a session deliverable) — Phase B must re-run.
**Confirmed; Phase B re-run completed 2026-04-29.**

---

### M-R2-5 — mid-sprint Tier 3 review — VALIDATES with procedural addendum

**Maps to FAI entries:** None (process, not primitive-semantics).

**Validation:** Mandatory mid-sprint Tier 3 at S4a-ii close-out (was S4a;
re-targeted post-S4a-split per Tier 3 verdict guidance #6) is correctly
scheduled per the original disposition. **Tier 3 trigger #5 ("Adversarial
review N≥2") fires independently for this sprint** under the new
`protocols/tier-3-review.md` v1.1.0; mid-sprint Tier 3 satisfies that
trigger.

**Procedural addendum (RESOLVED 2026-04-29):** Per
`protocols/adversarial-review.md` v1.1.0 § Outcome C, this sprint also
required a **Phase A independent design review (Tier 3 preferred)** —
separate from the mid-sprint Tier 3 at S4a-ii. The Phase A Tier 3 reviews
this Phase A re-entry package (FAI + re-validation findings) BEFORE Phase
B begins. The mid-sprint Tier 3 reviews the architectural-closure milestone
at S4a-ii.

**These are two distinct events** with different inputs and different
scopes:

| | Phase A Tier 3 (CONDUCTED 2026-04-29) | Mid-sprint Tier 3 (M-R2-5, scheduled at S4a-ii close-out) |
|---|---|---|
| When | Before Phase B re-run | At S4a-ii close-out, BEFORE S4b/S5a/S5b/S5c |
| Input | Phase A re-entry package (FAI + findings) | S4a-ii close-out + revised sprint package + revision-rationale chain |
| Scope | Validate FAI completeness; validate re-validated dispositions; validate measured-only escalation handling | Cross-layer composition validation; FAI cross-check at architectural-closure milestone; pending-reservation pattern + ceiling + `is_reconstructed` posture + callback-path atomicity invariant + reflective-call AST coverage |
| Verdict consequence | PROCEED → Phase B; **REVISE_PLAN → halt before Phase B** (this is what fired); PAUSE_AND_INVESTIGATE → halt sprint | PROCEED → S5a/S5b/S5c validation; REVISE_PLAN → halt validation; PAUSE_AND_INVESTIGATE → halt sprint |

RSK-PHASE-A-TIER-3-DEFERRED — **NOT FILED.** This Tier 3 occurred 2026-04-29.

---

### L-R2-1 / L-R2-2 / L-R2-3 — editorial — VALIDATE

**Maps to FAI entries:** None (editorial / scope / sizing, not
primitive-semantics).

**Validation:** All three are sound. L-R2-1's rephrasing aligns with the new
`templates/spec-by-contradiction.md` v1.1.0 rejection-rationale framing
(empirical falsification vs judgment call) — the rephrased rationales are
explicitly judgment calls, which the new template requires.

**L-R2-3 cumulative diff bound:** recalibrated from ~1100–1200 LOC to
**~1150–1300 LOC** per Tier 3 guidance, accommodating callback-path AST
guards (S4a-ii) + Branch 4 coupling (S3b per Tier 3 item C) + AC2.7
auto-activation (Decision 4) + `halt_entry_until_operator_ack` field
threading.

**No addenda needed beyond the cumulative-diff recalibration.**

---

## New finding from Phase A re-entry: cross-layer composition test (per `templates/sprint-spec.md` v1.2.0)

The new sprint-spec template adds a mandatory section **"Defense-in-Depth
Cross-Layer Composition Tests"** when DEC entries claim N≥3 layer defense.

**DEC-390 claims architectural closure of 4 layers** for DEF-204:

1. Atomic pending-sell reservation (`_reserve_pending_or_fail`).
2. Stop-replacement-vs-emergency-flatten differentiation
   (`is_stop_replacement` flag).
3. Locate-suppression-with-broker-verification (refresh-then-verify +
   Branch 4).
4. Startup CRITICAL warning + `--allow-rollback` gate (configuration safety).

Per the new template:

> When a sprint materializes a DEC entry that claims defense-in-depth across
> N≥3 layers (e.g., a 4-layer OCA defense; a 5-layer alert observability
> architecture), the regression checklist MUST include at least one test
> that exercises a *cross-layer composition path* — a scenario where the
> failure of one layer is supposed to be caught by another, asserting that
> the catch happens.

**Phase A re-entry initial proposal:** 3 tests (CL-1 / CL-2 / CL-3).

**Phase A Tier 3 sub-area D verdict:** "≥4 specific tests, with rationale
for any compositions left untested. Concrete additions beyond CL-1/2/3:
CL-4 (L1 + L2): Reservation succeeds but `is_stop_replacement` decision is
wrong; verify L3 ceiling catches the resulting over-flatten. CL-5 (L2 +
L3): `is_stop_replacement` correctly disambiguates a stop-replacement (L2
grants exemption) but locate-suppression for the position is active;
verify the protective stop-replacement path is allowed AND that Branch 4
does not falsely fire on it."

**Settled at Phase B re-run via Decision 5:** Sprint 31.92 commits to **5
tests (CL-1 through CL-5)** — above the template's "at least one" floor;
above Tier 3's 3-test floor. Tests live in S5c (NEW SESSION). **CL-6
(rollback + locate-suppression interaction) is explicitly OUT of Sprint
31.92** — defer with rationale documented in `docs/process-evolution.md`.
DEF-CROSS-LAYER-EXPANSION filed.

**The 5 cross-layer tests:**

> **CL-1 (L1 fails → L3 catches).** Force a `_reserve_pending_or_fail` false
> positive (mock the synchronous method to return True even when the ceiling
> would be exceeded). The post-emission state should trigger a
> ceiling-violation invariant check during reconciliation;
> locate-suppression-with-broker-verification (Layer 3) should fire on the
> ceiling-violation alert path.

> **CL-2 (L4 fails → L2 catches).** Force startup with `bracket_oca_type !=
> 1` AND `--allow-rollback` (the operator-confirmed rollback path). Verify
> that under DEC-386 rollback, the emergency-flatten branch (Layer 2 via
> `is_stop_replacement=False`) still ceiling-checks; this proves Layer 2
> doesn't depend on Layer 4's enforcement.

> **CL-3 (cross-layer falsification of FAI #2 + #5).** Force
> `Broker.refresh_positions()` timeout (Layer 3 fails) AND H1 selection by
> S1a output (entry #5 measured-only). Verify that the H-R2-2 HALT-ENTRY
> posture catches the composite — position marked
> `halt_entry_until_operator_ack=True`; no further SELL attempts; no
> phantom short. **Uses the new `SimulatedBrokerWithRefreshTimeout`
> fixture per Tier 3 item E / DEF-SIM-BROKER-TIMEOUT-FIXTURE.**

> **CL-4 (L1 + L2; NEW per Tier 3 sub-area D).** Reservation succeeds but
> `is_stop_replacement` decision is wrong (e.g., emergency-flatten
> misclassified as stop-replacement); verify L3 ceiling catches the
> resulting over-flatten.

> **CL-5 (L2 + L3; NEW per Tier 3 sub-area D).** `is_stop_replacement`
> correctly disambiguates a stop-replacement (L2 grants exemption) AND
> locate-suppression for the position is active. Verify the protective
> stop-replacement path is allowed AND that Branch 4 does not falsely fire
> on it.

This is a structural addition (Substantive vs Structural Rubric trigger #1
+ #2 + #6 — modifies regression checklist, modifies Hypothesis Prescription,
adds a session) — Phase B re-runs **completed 2026-04-29**.

---

## Substantive vs Structural assessment for Phase B re-run (UPDATED per Tier 3 verdict)

Per `protocols/adversarial-review.md` v1.1.0 § Substantive vs Structural
decision rubric, the following triggers fire across the Phase A re-entry
findings + the Phase A Tier 3 verdict:

- **Trigger #1** (introduces, modifies, or eliminates a Hypothesis Prescription
  entry): YES — H-R2-2 addendum modifies S1a halt-or-proceed gate language
  (was strengthened to N=100 hard gate per Decision 2).
- **Trigger #2** (introduces, modifies, or eliminates a primitive-semantics
  assumption in the FAI): YES — entry #8 was new at Phase A re-entry; entry
  #9 NEW per Tier 3 item A; entries #3 and #5 status promoted to
  unverified-with-falsifying-spike-scheduled per Decisions 1 + 2; entry
  #8 status promoted per Decision 3.
- **Trigger #3** (adds or modifies an ABC method): MARGINAL — `Broker.refresh_positions()`
  was already added by C-R2-1; Tier 3 item C extends it via the
  HALT-ENTRY coupling (no new ABC method, but the contract surface area
  grows). Not counted as a separate trigger firing.
- **Trigger #4** (third mechanism class neither original spec nor reviewer's
  alternative had): NO.
- **Trigger #5** (≥3 PARTIAL ACCEPT in single round): N/A — this is Phase A
  re-entry + Phase A Tier 3, not a round of adversarial review.
- **Trigger #6** (adds or removes a session in the session breakdown): YES —
  S1a internal scope expanded for FAI #3 + #5 sub-spikes; S4a split into
  S4a-i + S4a-ii (NEW SESSION per Tier 3 verdict guidance #3 + Decision 3);
  S5c NEW SESSION (cross-layer composition tests + `SimulatedBrokerWithRefreshTimeout`
  fixture per Tier 3 item E + Decision 5); +1 mid-sprint Tier 3 review
  event (M-R2-5) re-targeted to between S4a-ii and S4b. Net: 10 sessions
  → 13 sessions.
- **Trigger #7** (introduces a new RSK rated MEDIUM-HIGH or higher): YES —
  RSK-RECONSTRUCTED-POSITION-DEGRADATION re-rated to MEDIUM-HIGH per H-R2-3;
  RSK-FAI-COMPLETENESS (MEDIUM, NEW per Tier 3); RSK-CROSS-LAYER-INCOMPLETENESS
  (MEDIUM, NEW per Tier 3). RSK-PHASE-A-TIER-3-DEFERRED NOT filed (Tier 3
  occurred). RSK-FAI-COMPLETENESS at MEDIUM does not itself cross the
  trigger threshold; H-R2-3's MEDIUM-HIGH does.
- **Trigger #8** (modifies Hypothesis Prescription's halt-or-proceed gate
  language or FAI Status assignments): YES — multiple Status entries get
  resolved (from Phase A re-entry initial unverified to
  unverified-with-falsifying-spike-scheduled per Decisions 1/2/3); the
  H-R2-2 addendum modifies S1a gate language directly (N=100 hard gate
  added per Decision 2).

**Triggers fired: 5 of 8 (was 4 of 8 at Phase A re-entry initial authoring;
Trigger #2 fires re-counted to include entry #9 NEW per Tier 3 item A
plus the #3/#5/#8 Status promotions per Decisions 1/2/3 — single
trigger-class with multiple firings).** Phase B re-run is mandatory. The
disposition author MAY NOT apply revisions directly; structural revision
is required.

---

## Procedural concerns

### Concern 1: Round 3 scope contradicts new Outcome C protocol (RESOLVED)

**Round 2 disposition** (line 454) recommends Round 3 "biased toward
Assumption Mining only" — narrowest possible scope.

**`protocols/adversarial-review.md` v1.1.0 § Outcome C** requires *"Round
(N+2) adversarial review with **full scope, not narrowed**"* when ≥2
consecutive rounds caught Criticals of the same primitive-semantics class.

**Resolution:** The 2026-04-29 amendment supersedes the Round 2 disposition's
recommendation. Round 3 must be full scope. The Round 2 disposition was
authored before the protocol amendment; this is a normal protocol-evolution
correction.

**Action (COMPLETED at Phase C):** Phase C's Round 3 input package declares
full scope and includes the complete revised sprint package, not just a
delta against Round 2. See `adversarial-review-input-package-round-3.md`.

### Concern 2: Phase A independent design review missing from plan (RESOLVED)

**Round 2 disposition** Phase A activities list (line 432) includes 5 items;
none is an independent design review.

**`protocols/adversarial-review.md` v1.1.0 § Outcome C** requires Phase A
re-entry to include *"Independent design review (Tier 3 if available,
otherwise a fresh adversarial review with FULL scope, not narrowed)."*

**Resolution:** Phase A Tier 3 review #1 was conducted 2026-04-29. Inputs:
this Phase A re-entry findings document + the FAI artifact + the Round 2
disposition + Round 1 + Round 2 + Sprint Spec + SbC + Design Summary.
Output: Tier 3 verdict REVISE_PLAN per `tier-3-review-1-verdict.md`.

**Action (COMPLETED 2026-04-29):** Phase A Tier 3 conducted. Verdict
REVISE_PLAN. Phase B re-run mandatory; completed 2026-04-29.
RSK-PHASE-A-TIER-3-DEFERRED NOT filed.

### Concern 3: Outcome C requires Phase A be "scope-bounded but FULL FAI" (RESOLVED)

The protocol permits scope-bounded Phase A re-entry **but** requires:

1. ✅ FAI authoring (this artifact + companion).
2. ✅ Independent design review (Phase A Tier 3 review #1, 2026-04-29,
   verdict REVISE_PLAN).
3. 🔲 Round (N+2) full-scope adversarial review (after Phase B/C re-run —
   this is the next step).

The original disposition's "Phase A activities" implicitly attempted scope
narrowing on (2) and (3). The new protocol is explicit that scope-bounding
applies to which findings drive the re-entry but NOT to the review depth.

### Concern 4: Cross-Layer Composition Tests requirement is new and load-bearing (MATERIALIZED)

DEC-390's 4-layer claim activates the `templates/sprint-spec.md` v1.2.0
mandatory Cross-Layer section. The Origin comment in the template explicitly
references DEC-386's empirical falsification (60 phantom shorts on 2026-04-28
via cross-layer composition path that no single-layer test exercised). This
is the proximal trigger for Sprint 31.92 itself.

**Phase C MATERIALIZED 5 tests (CL-1 through CL-5)** in regression
checklist + S5c session per Decision 5; CL-6 explicitly out of scope per
Decision 5 with rationale in `docs/process-evolution.md`. Without this,
DEC-390 inherits DEC-386's empirical-falsification risk. The 5-test
commitment is above the template's "at least one" floor and above Tier 3
sub-area D's 3-test recommendation.

---

## Revised sequence to Phase D (UPDATED post-Tier-3)

| # | Activity | Output | Status |
|---|---|---|---|
| 1 | Phase A re-entry FAI + re-validation | `falsifiable-assumption-inventory.md` (8 entries) + `phase-a-reentry-findings.md` | ✅ 2026-04-29 |
| 2 | **Phase A Tier 3 independent design review #1** (per Outcome C) | `tier-3-review-1-verdict.md` (verdict REVISE_PLAN) | ✅ 2026-04-29 |
| 3 | Phase B design-summary re-run (incorporates FAI + re-validation outcomes + Tier 3 verdict + 7 settled operator decisions) | `design-summary.md` revised | ✅ 2026-04-29 |
| 4 | Phase C sprint-package revision: revised `falsifiable-assumption-inventory.md` (9 entries), revised `phase-a-reentry-findings.md` (this document), revised `sprint-spec.md` (with FAI section embedded), `spec-by-contradiction.md`, `session-breakdown.md` (13 sessions: S4a → S4a-i + S4a-ii; S5c NEW; mid-sprint Tier 3 inserted), `regression-checklist.md` (cross-layer tests added; invariants 23–27 NEW), `doc-update-checklist.md`, `escalation-criteria.md` (Decision 7 verbatim; A15/A16/A17 new triggers), new `adversarial-review-input-package-round-3.md` | 9 revised/new artifacts | ✅ this Phase C session 2026-04-29 |
| 5 | **Round 3 full-scope adversarial review** (not narrowed per Outcome C) | `adversarial-review-round-3-findings.md` + Round 3 disposition (if revisions needed; routed per Decision 7 binding pre-commitment) | next, separate Claude.ai conversation |
| 6 | Phase D session breakdown: implementation prompts + review prompts + review context + work journal handoff | Implementation prompts (10 sessions × impl + review pairs) + review context + work journal handoff | after Round 3 CLEAR or Decision 7 (b) disposition |
| 7 | Phase D execution reaches S4a-ii → mid-sprint Tier 3 (M-R2-5) | (already scheduled per M-R2-5; mid-sprint Tier 3 verdict artifact) | within sprint, ~mid-sprint |

**Total planning-only sessions before Phase D: 5** (Phase A initial + Phase
A Tier 3 + Phase B re-run + Phase C re-run + Round 3). Round 2 disposition
estimated 4. Delta: +1 (Phase A Tier 3 per Outcome C). **All five
completed or scheduled as of 2026-04-29.**

If Round 3 produces ≥1 Critical, **Decision 7 (operator pre-commitment)
binds the response**:
- (a) Foundational primitive-semantics-class miss → another revision pass
  (Phase A re-entry per Outcome C).
- (b) Any other Critical class → finding accepted as known limitation,
  logged as RSK at appropriate severity (MEDIUM-HIGH or higher per
  Severity Calibration Rubric), and sprint ships to implementation.

---

## Operator confirmation completed 2026-04-29 (recorded for audit)

Before scheduling the Phase A Tier 3 reviewer, the operator confirmed:

1. ✅ **Acknowledgment** that the FAI's 8 entries (at Phase A re-entry initial
   authoring) were complete to the operator's knowledge. Phase A Tier 3
   subsequently surfaced entry #9 (callback-path bookkeeping atomicity);
   the FAI's self-falsifiability clause fired correctly.
2. ✅ **Decision** on FAI #3 escalation: add adversarial sub-spike to S1a
   (Decision 1).
3. ✅ **Decision** on FAI #5 escalation: strengthen S1a `h1_propagation_converged`
   to cancel-then-immediate-SELL stress at N=100 (Decision 2 — N strengthened
   from 30 to 100 per Tier 3 sub-area B).
4. ✅ **Decision** on FAI #8 action: (a) S4a-ii regression sub-test for AST
   callsite scan adversarial cases (Decision 3 — option (a) chosen over (b)
   per Tier 3 sub-area B reversal).
5. ✅ **Decision** on M-R2-1 strengthening: auto-activate AC2.7 watchdog on
   first observed case-A in production (Decision 4).
6. ✅ **Decision** on the procedural concerns:
   - Round 3 scope: full (per protocol).
   - Phase A Tier 3: scheduled and conducted 2026-04-29.
   - Cross-layer composition tests: ≥4 added to Phase C scope per Decision 5
     (5 committed: CL-1 through CL-5; CL-6 explicitly out).
7. ✅ **Confirmation** that Substantive vs Structural Rubric triggers fire
   (5 of 8 post-Tier-3) and Phase B re-run is therefore mandatory; cannot
   apply revisions directly.
8. ✅ **Decision 6** on the roadmap-level question: Sprint 31.94 D3
   prioritization is NOT brought forward; Sprint 31.92 continues per Option
   A; D3 prioritization treated as a separate Discovery activity.
9. ✅ **Decision 7** on Round 3 escalation pre-commitment: operator-bound,
   verbatim binding contract for Round 3 outcome routing. Reproduced in
   `escalation-criteria.md` § Round 3 Outcome Pre-Commitment.

**All operator confirmations are auditable.** Decision 7 is the binding
contract for what happens after Round 3 produces a Critical; the
pre-commitment is written before Round 3 runs, not rationalized after the
fact. Operator override at Round 3 verdict time is permitted but must be
explicit and logged in the Round 3 disposition.
