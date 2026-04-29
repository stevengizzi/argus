# Sprint 31.92 — Phase A Tier 3 Review (Review #1) — Verdict

> **Stable repo verdict artifact** per `protocols/tier-3-review.md` v1.1.0
> § Output. Authored 2026-04-29 in Claude.ai conversation; preserved here to
> survive conversation rollover.
>
> **Trigger:** `protocols/adversarial-review.md` v1.1.0 § Outcome C —
> independent design review during Phase A re-entry after Round 1 + Round 2
> each caught Critical findings of the same primitive-semantics class
> (Round 1: asyncio yield-gap; Round 2: `ib_async` cache freshness). Tier 3
> trigger #5 (Adversarial review N≥2) and trigger #1 (safety-load-bearing
> footprint — `argus/execution/order_manager.py` 6 of 10 sessions)
> independently fire.
>
> **Inputs reviewed:** `falsifiable-assumption-inventory.md`,
> `phase-a-reentry-findings.md`, `round-2-disposition.md`,
> `revision-rationale.md` (Round 1), `sprint-spec.md`,
> `spec-by-contradiction.md`, `design-summary.md`.
>
> **Binding protocol versions:** `sprint-planning.md` v1.3.0,
> `adversarial-review.md` v1.1.0, `tier-3-review.md` v1.1.0,
> `templates/sprint-spec.md` v1.2.0, `templates/spec-by-contradiction.md`
> v1.1.0.

---

## Verdict: REVISE_PLAN

The Phase A re-entry artifacts do substantial good work — the FAI is a
serious-effort artifact, the re-validation re-checks all 14 dispositions,
and the procedural-deviations section correctly identifies all three.
**However, the FAI's self-falsifiability clause fires.** A primitive-
semantics assumption load-bearing on the L3 ceiling mechanism is missing
from the inventory, and the H-R2-1 disposition's structural protection is
narrower than the mechanism it protects. Phase B/C re-run is mandatory to
incorporate the missing entry and extend H-R2-1's protection scope. Round
3 proceeds at full scope (not narrowed) only after revisions land.

The verdict is REVISE_PLAN, not PAUSE_AND_INVESTIGATE — the meta-pattern
is unambiguous (three FAI-class misses across Round 1 + Round 2 + Phase A
Tier 3) but the fix is actionable within current sprint scope. See
§ "Operator decision item: meta-pattern severity" for the alternative.

---

## Sub-area A: FAI completeness (the falsification probe)

### Falsification result: inventory has failed

**Missing primitive-semantics assumption (proposed entry #9):**

> All bookkeeping update paths on `cumulative_pending_sell_shares` and
> `cumulative_sold_shares` (place-side increment, cancel/reject decrement,
> partial-fill transfer, full-fill transfer, `_check_sell_ceiling`
> multi-attribute read) execute synchronously between bookkeeping read and
> write across the entire transition. The L3 ceiling correctness depends
> on the asyncio single-event-loop guarantee applying to every path that
> mutates these counters, not only `_reserve_pending_or_fail`.

**Why this is load-bearing.** The L3 ceiling check reads two attributes
(`pending`, `sold`) and adds `requested`. If a callback path (e.g.,
`on_fill` processing a partial fill) yields between
`pending -= filled_qty` and `sold += filled_qty`, another coroutine's
ceiling check sees `pending` already decremented but `sold` not yet
incremented — total is artificially low — and a SELL that should be
blocked passes. This is exactly the structural class FAI #1 exists to
prevent, but FAI #1's AST guard + mocked-await injection test are scoped
narrowly to `_reserve_pending_or_fail`. The C-1 disposition's "AC3.1
enumerates all 5 state transitions; AC3.5 race test validates concurrency
safety" enumerates transitions in prose, but the structural protection
only covers one of them. The other four paths rely on implementation
discipline alone.

**Severity.** Per the Severity Calibration Rubric, MEDIUM-HIGH floor —
DEC-386's empirical falsification on 2026-04-28 is "a similar failure
mode in the same primitive-semantics class within the last 5 sprints."
Per Outcome C framing, this is a Critical-class finding for the FAI's
structural defense (the inventory has failed before being tested by Round
3).

**Required revision (drives REVISE_PLAN):**

1. Add FAI entry #9 with text per above.
2. Falsifying mechanism: extend the AST-no-await scan + mocked-await
   injection pattern to all callback paths that mutate the bookkeeping
   counters (`on_fill`, `on_cancel`, `on_reject`, `_on_order_status`).
3. Add S4a regression sub-test asserting the synchronous-update invariant
   on each callback path.
4. H-R2-1 disposition extension: the atomic-reserve protection is the
   reference pattern; the same guard applies to all bookkeeping paths.

### Borderline findings (flagged but not driving REVISE_PLAN)

**#B1 — `positionEndEvent` steady-state semantics.** FAI #2's S3b spike
measures cache staleness under reconnect-window conditions only. Steady-
state behavior under high-volume position updates (reachable in production
with hundreds of variants) is not separately falsified. Recommendation:
extend FAI #2's scope text to cover both axes, or document high-volume as
explicitly out of scope.

**#B2 — SimulatedBroker cannot exercise Branch 4.** Per L-R2-3,
`SimulatedBroker.refresh_positions()` is "no-op or instant-success." In-
process validation tests Branch 1/2/3 only; Branch 4 (`verification_stale:
true`) is exercised only in S3b paper spike — no unit-test analog.
Recommendation: add `SimulatedBrokerWithRefreshTimeout` fixture variant at
S5b.

These are MEDIUM findings, incorporated alongside entry #9 in Phase B/C.

---

## Sub-area B: Measured-only escalation handling

**FAI #3 (modifyOrder determinism).** Recommended axes (i) concurrent
amends, (ii) reconnect-window amends, (iii) stale-ID amends are sound and
falsifying. Not exhaustive (missing: EOD windows, CLOSING-state, high-tick
auctions) but FAI does not claim exhaustiveness; Wilson-UB-on-worst-axis
gate is conservative. **Acceptable as proposed.**

**FAI #5 (`await_propagation` atomicity).** Cancel-then-immediate-SELL
stress with N≥30 is genuinely falsifying, but **N=30 is statistically
weak** given catastrophic-loss consequences of H1 selection. Wilson UB on
0/30 is roughly [0%, 11.6%] — all-30-green still permits ~1-in-9
production failures. **Recommendation: increase N to ≥100** (operationally
feasible during a single pre-market window). Hard-gate semantic (any
conflict in 30 → H1 ineligible) is correct; N just needs to be tighter.

**FAI #4 (locate-rejection string stability).** Acceptable with M-R2-1
auto-activation strengthening. **FAI #6 (case A vs B).** Genuinely
falsifying. **FAI #1 (asyncio synchronicity).** Status correct for the
*narrow* scope; the *broad* assumption needs entry #9 per Sub-area A.
**FAI #7 (`on_position_closed` coverage).** Genuinely falsifying via
M-R2-2. **All acceptable as classified.**

**FAI #8 (AST callsite scan completeness).** Findings document prefers
option (b) accept-and-document. **This Tier 3 prefers option (a)** — the
static analysis IS the load-bearing defense for invariant 24; accepting a
known-coverage-gap weakens that defense. Cost is three test cases; value
is closing the falsification surface. Operator may override on cost-
benefit, but the floor recommendation is option (a).

---

## Sub-area C: Round 2 disposition re-validation

The findings document is sound for 13 of 14 dispositions. **One missed
addendum:**

**H-R2-1 (atomic `_reserve_pending_or_fail`) — needs scope extension.**
Findings document records "no addendum needed." Per Sub-area A finding
#9, the disposition's protection is narrower than the L3 ceiling
mechanism's correctness scope. Phase C must extend the AST-no-await guard
+ mocked-await injection pattern to all bookkeeping callback paths.

The remaining 13 dispositions re-validate as the findings document
records. Proposed strengthenings — C-R2-1 + H-R2-2 coupling
(halt_entry_until_operator_ack=True under H1 active AND refresh fails),
M-R2-4 adversarial sub-spike, M-R2-1 auto-activation, H-R2-5 FAI #8 — are
all sound. The H-R2-2 addendum's tightened halt-or-proceed gate language
(worst-of Wilson-UB AND zero-conflict-stress) is the right shape; only
refinement is increasing N per Sub-area B.

---

## Sub-area D: Cross-Layer Composition Tests

**Cross-layer test count: candidate scenarios are sound but at the
floor.** CL-1/CL-2/CL-3 exceed the template's "at least one" — three
candidates is technically sufficient.

**The floor is not the right bar given DEC-386's lesson.** DEC-386's
empirical falsification was via a cross-layer composition path that no
single-layer test exercised. The 4-layer architecture has multiple
composable runtime pairs (L1+L2, L1+L3, L2+L3) reachable in production.
CL-1/2/3 cover three; ~2-3 remain unexercised.

**Recommended: ≥4 specific tests, with rationale for any compositions
left untested.** Concrete additions beyond CL-1/2/3:

- **CL-4 (L1 + L2):** Reservation succeeds but `is_stop_replacement`
  decision is wrong (e.g., emergency-flatten misclassified as stop-
  replacement). Verify L3 ceiling catches the resulting over-flatten.
- **CL-5 (L2 + L3):** `is_stop_replacement` correctly disambiguates a
  stop-replacement (L2 grants exemption) but locate-suppression for the
  position is active. Verify the protective stop-replacement path is
  allowed AND that Branch 4 does not falsely fire on it.

L4 (config-time startup warning) compositions with runtime layers are
weakly meaningful; CL-2 covers the operationally-relevant case.

**Required revision:** Phase C commits to ≥4 specific tests (CL-1, CL-2,
CL-3, plus at least one of CL-4/CL-5), with written rationale for any
compositions left untested.

---

## Sub-area E: Procedural deviations

**Findings document correctly characterizes all three:**

1. Round 3 scope must be full, not narrowed (Round 2 disposition
   superseded by 2026-04-29 amendment).
2. Phase A Tier 3 is required (this conversation satisfies it).
3. Cross-Layer Composition Tests are mandatory (template v1.2.0).

**No additional deviations of high severity were missed.** Two minor
refinements: (a) Phase B/C planner should explicitly plan for a
CRITICAL-finding scenario in Round 3 with abort path to operator
escalation; (b) RSK severity calibration audit-passes for all proposed
RSKs at Round-2-recommended severities.

---

## Operator decision items

These items require operator decision before Phase B begins:

1. **FAI #3 escalation:** add S1a adversarial sub-spike (recommended) OR
   retain measured-only with RSK-S1A-ADVERSARIAL-UNTESTED MEDIUM-HIGH.
2. **FAI #5 escalation:** strengthen S1a `h1_propagation_converged` to
   cancel-then-SELL stress AND increase N from ≥30 to ≥100 (recommended)
   OR retain measured-only.
3. **FAI #8 action:** option (a) S4a regression sub-test (recommended)
   OR option (b) accept-and-document.
4. **M-R2-1 strengthening:** auto-activate AC2.7 watchdog on first
   observed case-A in production (recommended) OR keep manual.
5. **Cross-layer test count:** commit to ≥4 specific tests (recommended)
   OR leave at floor with explicit rationale.
6. **Roadmap-level question (deferred from Round 2):** should Sprint
   31.94 D3 be prioritized ahead of 31.93? FAI #5 escalation does NOT
   directly sharpen this — reconstructed positions already refuse SELLs
   per AC3.7, so H1's safety on reconstructed positions is moot. **No
   new sharpening from this Tier 3.** Question stands as a separate
   Discovery activity.

### Operator decision item: meta-pattern severity

**Three FAI-class primitive-semantics misses have now occurred:** Round
1 (asyncio yield-gap), Round 2 (ib_async cache freshness), Phase A Tier
3 (callback-side state-transition atomicity). The 2026-04-29 protocol
amendments were authored after Round 1 + Round 2 specifically to install
the FAI as the structural defense. The defense itself missed an entry
on first authoring.

**This verdict treats the meta-pattern as actionable** (REVISE_PLAN)
rather than escalation (PAUSE_AND_INVESTIGATE). Three judgments support
this: (a) the missing FAI entry is mechanically simple to add; (b) Round
3 at full scope provides the protocol-level catch for further misses;
(c) remaining work to seal Sprint 31.92 is bounded.

**Operator may override to PAUSE_AND_INVESTIGATE if any of:**

- Sprint 31.92's remaining work has expanded enough that another revision
  pass exceeds operational tolerance.
- Round 3 producing a fourth Critical seems likely enough to plan for the
  abort path now.
- Bringing Sprint 31.94 D3 forward seems comparable in cost to completing
  31.92 + 31.93 first.

The operator's call. This verdict's recommendation is REVISE_PLAN with
the meta-pattern flagged in Phase B handoff and Round 3 escalation
criteria.

---

## DEC entries authored / revised

**None at this verdict.** No architectural decisions are being made or
revised. DEC-390 materializes at sprint-close, incorporating the revised
mechanism with entry #9's protection extended.

---

## DEF entries filed

**DEF-FAI-CALLBACK-ATOMICITY** — Extend `_reserve_pending_or_fail`'s
AST-no-await guard + mocked-await injection regression pattern to all
bookkeeping callback paths. **Sprint target: 31.92 Phase B/C re-run
(in-sprint).** Sprint-gating: Round 3 advancement gated on this DEF —
Round 3 reviewer's FAI cross-check explicitly confirms entry #9 +
extended H-R2-1 protection.

**DEF-CROSS-LAYER-EXPANSION** — Cross-layer composition tests at floor
(3) rather than coverage-comprehensive (≥4). Phase C commits to ≥4 with
rationale. **Sprint target: 31.92 Phase C re-run.**

**DEF-FAI-N-INCREASE** — FAI #5 cancel-then-SELL stress N=30 statistically
weak; increase to N≥100. **Sprint target: 31.92 S1a sub-spike refinement.**
Operator-overridable on cost grounds.

**DEF-FAI-2-SCOPE** — FAI #2 spike scope reconnect-window only; high-
volume steady-state semantics unverified. Extend or document out-of-scope.
**Sprint target: 31.92 (documentation); Sprint 31.94 (implementation if
deferred).**

**DEF-FAI-8-OPTION-A** — H-R2-5 / FAI #8 should choose option (a)
adversarial regression sub-test rather than option (b) accept-and-
document. **Sprint target: 31.92 S4a.** Operator-overridable.

**DEF-SIM-BROKER-TIMEOUT-FIXTURE** — `SimulatedBroker` cannot exercise
Branch 4 timeout path. Add `SimulatedBrokerWithRefreshTimeout` fixture at
S5b. **Sprint target: 31.92 S5b.**

---

## RSK entries filed

**RSK-FAI-COMPLETENESS** — FAI's self-falsifiability clause triggered
during Phase A Tier 3 (entry #9 added). Pattern of recurring FAI misses
suggests Round 3 may surface a fourth. Mitigation: Phase B/C re-run +
Round 3 full-scope cross-check; if Round 3 surfaces a Critical, Outcome
C re-fires. **Severity: MEDIUM** (mitigation in-sprint; bounded by Round
3 cycle).

**RSK-CROSS-LAYER-INCOMPLETENESS** — Cross-layer composition tests
provisionally at 3-test floor. Mitigation: Phase C commits to ≥4 tests.
**Severity: MEDIUM** (DEC-386's empirical falsification justifies
heightened bar).

**RSK-PHASE-A-TIER-3-DEFERRED** — NOT FILED. This Tier 3 occurred.

---

## Inherited follow-ups by sprint

**Sprint 31.92 (current — Phase B/C re-run):** Add FAI #9; extend H-R2-1
to callback paths; FAI #2 scope text; FAI #5 N≥100; FAI #8 option (a);
≥4 cross-layer tests; C-R2-1 + H-R2-2 coupling; M-R2-1 auto-activation;
M-R2-4 adversarial sub-spike; Round 3 escalation criteria explicit.

**Sprint 31.93 (component-ownership):** Inherits prior items. **NEW
from this Tier 3:** if FAI's callback-path AST-guard pattern becomes a
project-wide invariant, 31.93 must preserve it during refactor (regression-
checklist invariant added).

**Sprint 31.94 (reconnect-recovery + boot-time policy):** Inherits prior
items + RSK-DEC-386-DOCSTRING bound. **NEW from this Tier 3:** FAI #2
scope-text amendment (high-volume axis) lands here if 31.92 documents
high-volume as out-of-scope.

**Sprint 35+ (Learning Loop V2):** Inherits DEF-209 extended scope. **NEW
from this Tier 3:** if SQLite persistence lands for bookkeeping counters,
synchronous-update invariant (entry #9) extends to persistence layer
(write-then-flush atomicity). Filed forward.

---

## Document updates required at Phase B/C re-run

`falsifiable-assumption-inventory.md` — add entry #9; update scope text
on entries #2, #5, #8. `phase-a-reentry-findings.md` — add H-R2-1
addendum. `sprint-spec.md` — reproduce updated FAI; H-R2-1 / AC3.5 race
test extends to callback paths. `spec-by-contradiction.md` — § Edge Cases
to Reject #1 acknowledges broader contract. `design-summary.md` — pytest-
Δ may shift +2 to +4 across S2a/S2b/S3a/S3b/S4a; Regression Invariants
adds the broader synchronous-update invariant. `session-breakdown.md` —
re-check S4a + S5b compaction-risk scores. `regression-checklist.md` —
invariant 13 extends to all bookkeeping paths; CL-4/CL-5 added.
`escalation-criteria.md` — Round 3 abort path explicit.
`adversarial-review-input-package-round-3.md` — declare full scope; FAI
cross-check explicit. `CLAUDE.md` — DEF table additions (6 DEFs).
`docs/risk-register.md` — RSK-FAI-COMPLETENESS,
RSK-CROSS-LAYER-INCOMPLETENESS. `docs/process-evolution.md` — at sprint-
close: "Phase A re-entry FAI authoring is itself subject to first-pass
miss; Phase A Tier 3 catches what spec-author misses; Round 3 full-scope
catches what Phase A Tier 3 misses."

No updates at this verdict to `decision-log.md`, `dec-index.md`,
`architecture.md`, `project-knowledge.md`, or
`pre-live-transition-checklist.md` — those are sprint-close concerns.

---

## Workflow protocol gaps surfaced

**No new protocol amendments recommended.** The 2026-04-29 amendments are
working as intended. The FAI made entry #9's miss DETECTABLE during
Phase A Tier 3; without it, this gap would have surfaced at best in
Round 3, at worst in production. The three-outcome state machine routed
Sprint 31.92 correctly back to Phase A. The Substantive vs Structural
rubric correctly fired multiple triggers. Cross-Layer Composition Tests
requirement surfaced a coverage gap.

**Process-evolution observation** (not a protocol amendment): the Phase
A Tier 3 review's workload is comparable to a full adversarial round.
By design (it IS effectively the adversarial review per Outcome C's
"Tier 3 if available, otherwise fresh adversarial review"). A "scope-
bounded" Phase A re-entry per Outcome C still includes a full-scope
independent design review.

---

## Guidance for Phase B planner

1. **Re-run Substantive vs Structural Rubric.** Triggers fired: #1
   (Hypothesis Prescription modification — H-R2-2 addendum), #2 (FAI
   modification — entry #9 + #3/#5/#8 re-rated), #6 (session breakdown
   additions), #8 (halt-or-proceed gate language modified). **5 of 8
   triggers fired.** Phase B re-run mandatory.

2. **Materialize verdict's revisions in Phase B Design Summary.** Do
   NOT proceed to Phase C until Design Summary reflects: FAI entry #9 +
   revised falsifying mechanism for H-R2-1; borderline #B1+#B2
   acknowledged; cross-layer test count committed (≥4); C-R2-1 +
   H-R2-2 coupling; M-R2-1 auto-activation; M-R2-4 adversarial sub-
   spike; FAI #8 option (a); FAI #5 N≥100.

3. **Re-validate session count after Phase B/C edits.** S1a +2 to +3,
   S4a + several from callback-path regression tests, S5b + small from
   timeout fixture. Verify against compaction-risk thresholds.

4. **Round 3 input package declares full scope.** Per Outcome C, do NOT
   propose narrowed scope. FAI cross-check is mandatory and explicit.

5. **Round 3 escalation criteria explicit.** If Round 3 produces ≥1
   Critical (regardless of class), Outcome C re-fires. Document must
   state: "Sprint 31.92 abort path triggers; operator escalation re:
   Sprint 31.94 D3 prioritization as alternative to another revision
   pass."

6. **Mid-sprint Tier 3 (M-R2-5) remains scheduled.** This Phase A Tier
   3 does NOT replace it. Two distinct events with different inputs and
   scopes.

---

## Cross-references

- **DEC-385 (Sprint 31.91):** 6-layer Side-Aware Reconciliation. Branch
  4 reuses `phantom_short_retry_blocked`. No modification.
- **DEC-386 (Sprint 31.91):** 4-layer OCA-Group Threading. Empirically
  falsified 2026-04-28 (60 phantom shorts via cross-layer composition).
  Proximal trigger for Sprint 31.92 + 2026-04-29 protocol amendments +
  this Tier 3.
- **DEC-388 (Sprint 31.91):** Alert Observability. POLICY_TABLE extended
  with 14th entry per AC3.9.
- **DEF-204:** PRIMARY DEFECT. Sprint 31.92 target. Closure gated by
  criterion #5 (5 paper sessions clean post-seal) and #6 (Sprint 31.94
  sealed).
- **DEF-211 (D1+D2+D3):** strictly OUT of Sprint 31.92.
- **DEF-212:** Sprint 31.92 L4 rider; no modification from this Tier 3.

---

## Closing

Phase A re-entry's FAI is a serious-effort artifact and demonstrates the
value of the 2026-04-29 protocol amendments. The FAI made entry #9's
miss detectable; without the FAI, this primitive-semantics gap would
have surfaced — at best — in Round 3 at full scope, and — at worst — in
production paper trading. That Phase A Tier 3 caught it is the protocol
working as designed.

The verdict is REVISE_PLAN. Phase B/C re-run incorporates the missing
entry, extends H-R2-1's structural protection, refines FAI #5 sample
size, commits to ≥4 cross-layer tests, and applies the strengthenings
the findings document already proposed. Round 3 proceeds at full scope
with the FAI cross-check applied to the revised inventory.

If the meta-pattern of recurring primitive-semantics misses concerns the
operator more than the actionability suggests, PAUSE_AND_INVESTIGATE is
the alternative — escalate to roadmap-level re-prioritization rather
than another revision pass.
