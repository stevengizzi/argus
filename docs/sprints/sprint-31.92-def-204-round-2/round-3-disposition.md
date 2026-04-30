# Sprint 31.92 — Round 3 Disposition

> Disposition author: operator (Steven), with reviewer recommendations folded in
> Date: 2026-04-29
> Round 3 verdict: Outcome B — 1 Critical + 5 High + 4 Medium + 2 Low; A14 fired
> Reviewer recommendation: Decision 7 (a) — Phase A re-entry per Outcome C
> **Operator disposition: Decision 7 (b) with explicit operator override** — see § 1 Operator Override Invocation below
> Companion artifact: `adversarial-review-round-3-findings.md` (Round 3 verdict)

---

## 1. Operator Override Invocation (per Decision 7 verbatim)

Decision 7 (verbatim from `escalation-criteria.md` § Round 3 Outcome
Pre-Commitment) provides:

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
  RSK-REFRESH-POSITIONS-CONCURRENT-CALLER at CRITICAL severity (per § 4
  below).
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
- This disposition document (logged at sprint folder root)
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

## 2. Critical Finding Disposition

### 2.1 C-R3-1 — `Broker.refresh_positions()` concurrent-caller correlation

**Disposition:** **PARTIAL ACCEPT (different)** — RSK + in-sprint
structural fix.

**RSK filed:** RSK-REFRESH-POSITIONS-CONCURRENT-CALLER (CRITICAL).
Mitigation: Fix A (single-flight serialization) committed in-sprint at
S3b. See § 4 Risk Register Updates below.

**FAI extension committed:** FAI #10 added at S3b sprint-close
(materialization timing per Decision 7 (b) routing). See § 5 FAI
Updates below.

**Cross-Layer test addition:** CL-7 added at S5c. See § 6
Session-Breakdown Deltas below.

**Spec-text amendments required:** see § 7 Spec Amendment Manifest below
(specifically items 1–4 — `IBKRBroker.refresh_positions()` body
amendment, AC2.5 amendment for serialization wrapper, Performance
Benchmarks table addition, Config Changes table addition).

---

## 3. High Findings Dispositions

All 5 High findings: **ACCEPT**. Spec-text amendments folded into a
single amendment cycle (Step 2 of the runway plan); fixes implemented
in-spec-text BEFORE Phase D prompt generation.

### 3.1 H-R3-1 — `time.time()` → `time.monotonic()` for suppression timeout

**Disposition:** ACCEPT verbatim per reviewer's Fix Shape.

**Spec amendment scope:** AC2.2, AC2.3, all four standalone-SELL
exception handlers (the 4 places that set `_locate_suppressed_until`
entries), and the AC2.5 timeout-check site. Also: Sprint Spec § Config
Changes table footnote on `locate_suppression_seconds` validator.

**Regression test:** `test_locate_suppression_resilient_to_wall_clock_skew`
added to S3b regression scope.

**LOC impact:** ~5 LOC in `argus/execution/order_manager.py` + ~10 LOC
test. Within budget.

### 3.2 H-R3-2 — Decision 4 watchdog `auto`→`enabled` flip semantics

**Disposition:** ACCEPT verbatim per reviewer's Fix Shape.

**Spec amendment scope:** AC2.7 amended to specify:
- **Storage:** in-memory Pydantic field mutation only; no persistence;
  restart resets to `auto`.
- **Event-definition:** "first observed `case_a_in_production`" =
  globally-scoped, single ARGUS process lifetime, defined as: first
  time `_pending_sell_age_seconds` exceeds threshold AND no fill
  observed AND `_locate_suppressed_until[position.id]` is set, in any
  position.
- **Atomicity:** flip guarded by `asyncio.Lock` in watchdog detection
  path; re-entrant flips are no-ops (idempotent).
- **Logged transition:** structured log line `event="watchdog_auto_to_enabled"`
  on flip with `case_a_evidence: {position_id, symbol, age_seconds_at_flip}`.

**RSK addition:** RSK-WATCHDOG-AUTO-FLIP-RESTART-LOSS (MEDIUM). See § 4.

**LOC impact:** ~25 LOC. Within budget.

### 3.3 H-R3-3 — `halt_entry_until_operator_ack` consumer + clearing mechanism

**Disposition:** ACCEPT verbatim per reviewer's Fix Shape.

**Spec amendment scope:** new AC2.8 added (was implicit in AC2.5 Branch
4); specifies:
- **Consumer:** RiskManager Check 0 (existing DEC-027) extended to also
  reject entries when ANY ManagedPosition has `halt_entry_until_operator_ack=True`
  AND the entry signal is for the SAME `ManagedPosition.id`. Per-position
  granularity preserved; new positions on same symbol unaffected.
- **Ack mechanism:** new REST endpoint `POST /api/v1/positions/{position_id}/clear_halt`
  + new CLI tool `scripts/clear_position_halt.py {position_id}`. No Web
  UI changes (per SbC §13).
- **Restart behavior:** halt-entry flag does NOT survive restart; the
  `is_reconstructed=True` posture (AC3.7) subsumes halt-entry by
  refusing ALL ARGUS-emitted SELLs on reconstructed positions.
- **Logged transitions:** `event="halt_entry_set"` on Branch 4 + H1
  firing; `event="halt_entry_cleared"` on operator-ack via CLI/REST.

**Test additions:** `test_risk_manager_check0_rejects_when_halt_entry_set`
+ `test_clear_halt_endpoint_requires_position_id_and_clears_flag`.

**LOC impact:** ~70 LOC across `argus/risk/risk_manager.py`,
`argus/api/v1/positions.py` (new), `scripts/clear_position_halt.py`
(new). Distributed across files; OrderManager budget unaffected.

### 3.4 H-R3-4 — AC4.6 dual-channel CRITICAL warning hardening

**Disposition:** ACCEPT verbatim per reviewer's Fix Shape (interactive
ack + periodic re-ack + CI-override flag separation).

**Spec amendment scope:** AC4.6 amended to add:
- **Startup-time interactive ack** (default ON for non-CI environments):
  when `bracket_oca_type != 1` AND `--allow-rollback` AND interactive
  TTY detected, ARGUS prompts for exact phrase "I ACKNOWLEDGE ROLLBACK
  ACTIVE"; anything else exits with code 3.
- **Periodic re-ack:** every 4 hours during runtime, ntfy.sh
  `system_warning` urgent + canonical-logger CRITICAL with phrase
  "DEC-386 ROLLBACK ACTIVE — STILL IN ROLLBACK STATE — N hours since
  startup".
- **CI override flag:** `--allow-rollback-skip-confirm` (separate from
  `--allow-rollback`) bypasses the interactive prompt for unattended
  starts. Both flags required for CI use.

**New Edge Case to Reject:** SbC #19 (NEW) — "`--allow-rollback-skip-confirm`
used in production startup scripts. The flag exists for CI ONLY;
production startup MUST require the interactive ack."

**LOC impact:** ~30 LOC in `argus/main.py` + ~10 LOC CI fixture updates.
Within budget.

### 3.5 H-R3-5 — AC3.1 callsite-enumeration AST exhaustiveness guard

**Disposition:** ACCEPT verbatim per reviewer's Fix Shape.

**Spec amendment scope:** AC3.5 extended (per Tier 3 items A + B + new
H-R3-5) to include the AST exhaustiveness test. AC3.1 footnote added:
"the synchronous-update invariant scope is enforced by FAI #11
exhaustiveness regression at S4a-ii."

**FAI extension committed:** FAI #11 added at S4a-ii sprint-close.

**Test addition:** `test_bookkeeping_callsite_enumeration_exhaustive`
added to S4a-ii regression scope (~40 LOC including helper).

**LOC impact:** ~40 LOC test. Within budget.

---

## 4. Medium + Low Findings Dispositions

### 4.1 M-R3-1 — S1a worst-axis Wilson UB axis-combination gap

**Disposition:** ACCEPT — Option (a) per reviewer (extend S1a with 4th
axis). S1a script extended with axis (iv): concurrent amends across
N≥3 positions DURING reconnect window. Halt-or-proceed gate uses
`worst_axis_wilson_ub` across all 4 axes. JSON output schema gains
`adversarial_axis_iv_results`.

**LOC impact:** ~50 LOC in `scripts/spike_def204_round2_path1.py`. Spike
runtime increases ~10 minutes. Within budget.

### 4.2 M-R3-2 — AC2.5 Branch 4 alert idempotency

**Disposition:** ACCEPT verbatim per reviewer's Fix Shape. AC2.5
amended to specify Branch 4 firings on the same `ManagedPosition.id`
within a session are throttled — first firing publishes; subsequent
within 1 hour are suppressed at alert layer (logged INFO with
`branch_4_throttled: true`); HALT-ENTRY effect persists; throttle
resets on `on_position_closed` or successful refresh observation.

**LOC impact:** ~30 LOC. Within budget.

### 4.3 M-R3-3 — Same-position concurrent `modify_order` not tested by S1a

**Disposition:** PARTIAL ACCEPT — per reviewer's Fix Shape, S2a
implementation prompt extended with precondition check for existing
per-position serialization on `_trail_flatten`. If existing
serialization is found, document and proceed; if not, halt and surface
to operator before implementing H2.

**LOC impact:** ≤10 LOC if mitigation needed; documentation otherwise.

### 4.4 M-R3-4 — `refresh_positions`-then-`get_positions` no-await invariant

**Disposition:** ACCEPT verbatim per reviewer's Fix Shape. New helper
`_read_positions_post_refresh()` added on OrderManager; AC2.5 fallback
calls helper instead of direct sequence; S4a-ii regression scope
extended to include the helper's body in the AST-no-await scan.

**LOC impact:** ~15 LOC. Within budget.

### 4.5 L-R3-1 — Pydantic config field mutation atomicity

**Disposition:** ACCEPT — covered by H-R3-2 fix shape.

### 4.6 L-R3-2 — `--allow-rollback` flag persistence across systemd restarts

**Disposition:** ACCEPT — covered by H-R3-4 fix shape (interactive ack
forces operator presence; periodic re-ack bounds silent persistence to
4-hour windows).

---

## 5. Risk Register Updates (NEW for this disposition)

### 5.1 RSK-REFRESH-POSITIONS-CONCURRENT-CALLER (NEW, CRITICAL)

**Severity:** CRITICAL (per Severity Calibration Rubric §"failure mode
produces unrecoverable financial loss within single trading session" —
phantom-short class).

**Description:** `Broker.refresh_positions()` is implemented atop a
session-global `positionEndEvent` with no per-caller correlation. Under
concurrent callers (realistic at AC2.5 timeout-fallback firing rates
during locate-rejection storms — empirically observed Apr 28 with 60
NEW phantom shorts clustering), one caller's `wait_for` may return
successfully on another caller's `positionEnd`, leading to
stale-for-this-caller cache reads in Branch 1/2/3 classification.
Branch 4's refresh-failure detection does NOT catch this case because
`wait_for` returns successfully.

**Mitigation (in-sprint structural fix at S3b):** Fix A — single-flight
`asyncio.Lock` + 250ms coalesce window on `IBKRBroker.refresh_positions()`.
Coroutine A's lock acquisition serializes coroutine B's call; if B's
call arrives within 250ms of A's cache-synchronization timestamp, B
returns immediately (cache IS fresh per A's broker round-trip). Outside
the coalesce window, B acquires the lock and performs its own
synchronized broker round-trip.

**Falsification:** FAI #10 (NEW) — falsifying spike at S3b: spawn N=20
coroutines calling `refresh_positions()` near-simultaneously (≤10ms
separation), assert the race IS observable WITHOUT the serialization
mitigation (mocked-await injection between A's reqPositions and B's
reqPositions, deterministic broker state-change between); assert race
is NOT observable WITH the mitigation. Cross-Layer test CL-7 (NEW at
S5c) exercises composite: N=2 concurrent AC2.5 fallbacks, broker state
mutated between callers, assert no stale Branch 2 classification.

**Cessation criterion:** mitigation removed only when FAI #10 spike
returns green AND CL-7 returns green AND mid-sprint Tier 3 review
(M-R2-5) PROCEED verdict on the C-R3-1 fix.

### 5.2 RSK-WATCHDOG-AUTO-FLIP-RESTART-LOSS (NEW, MEDIUM)

**Severity:** MEDIUM (operational hygiene; partially-mitigated by
post-restart `is_reconstructed=True` refusal posture).

**Description:** AC2.7's Decision 4 `auto`→`enabled` flip is in-memory
only and does not survive ARGUS restart. If a case-A storm happened
pre-restart and ARGUS restarts during the storm, the post-restart
process operates with watchdog disabled until another case-A
observation. Reconstructed positions are protected by AC3.7's refusal
posture; new positions entered post-restart that hit case-A before the
watchdog re-enables are exposed.

**Mitigation:** post-restart, `reconstruct_from_broker` populates
`is_reconstructed=True`, refusing ARGUS-emitted SELLs entirely; the
missing watchdog is moot for reconstructed positions. Residual risk is
narrow (NEW positions, post-restart, hitting case-A before re-enable).
Sprint 31.94 D3's policy decision retires the `is_reconstructed`
conservative posture; this RSK is bounded by Sprint 31.94 D3.

---

## 6. FAI Updates

### 6.1 FAI #10 — `Broker.refresh_positions()` concurrent-caller correlation (NEW)

**Materialization:** committed in this disposition; materialized at S3b
sprint-close (per Decision 7 (b) operator-override rationale). FAI text
inserted into `falsifiable-assumption-inventory.md` at S3b close-out as
part of S3b's structured close-out artifact.

**Text:**

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
> Condition #N (NEW): if Fix A spike fails AND no alternative
> serialization design, sprint halts and operator decides whether to
> escalate to Phase A re-entry retroactively.

### 6.2 FAI #11 — Bookkeeping callsite-enumeration exhaustiveness (NEW)

**Materialization:** committed in this disposition; materialized at
S4a-ii sprint-close. FAI text inserted at S4a-ii close-out.

**Text:**

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

---

## 7. Spec Amendment Manifest

This manifest is the **consumer contract** per `protocols/mid-sprint-doc-sync.md`
v1.0.0. The Step 2 spec amendment cycle (separate Claude.ai
conversation) consumes this manifest and produces the surgical edits
to Phase C artifacts.

### 7.1 `sprint-spec.md` amendments

| Section | Amendment | Source |
|---------|-----------|--------|
| Deliverable 2 | Add: "`IBKRBroker.refresh_positions()` body uses single-flight `asyncio.Lock` + 250ms coalesce window per Round 3 C-R3-1 disposition. Concurrent callers serialized; rapid-succession callers benefit from coalesce." | C-R3-1 Fix A |
| AC2.2 | Replace `time.time()` with `time.monotonic()` in suppression-check site | H-R3-1 |
| AC2.3 | Replace `time.time()` with `time.monotonic()` in 4 standalone-SELL exception handlers | H-R3-1 |
| AC2.5 | Add: "`refresh_positions()` is single-flight serialized per Round 3 C-R3-1 disposition; the timeout still applies (5s per call); concurrent callers either await the lock (within their own 5s budget) or coalesce on the prior caller's synchronization (250ms window)." | C-R3-1 |
| AC2.5 | Add Branch 4 throttle: "Branch 4 firings on the same `ManagedPosition.id` within a session are throttled to one per hour at alert layer; HALT-ENTRY effect persists; throttle resets on `on_position_closed` or successful refresh observation." | M-R3-2 |
| AC2.7 | Replace section with H-R3-2 Fix Shape: storage (in-memory only, restart resets); event-definition (globally-scoped); atomicity (`asyncio.Lock` guard, idempotent re-entrant flips); logged transition. | H-R3-2 |
| AC2.8 (NEW) | Add new AC: `halt_entry_until_operator_ack` consumer (RiskManager Check 0 extended), ack mechanism (new REST endpoint + CLI tool), restart behavior (subsumed by `is_reconstructed=True`), logged transitions. | H-R3-3 |
| AC3.1 | Add footnote: "synchronous-update invariant scope is enforced by FAI #11 exhaustiveness regression at S4a-ii." | H-R3-5 |
| AC3.5 | Extend test scope: include `test_bookkeeping_callsite_enumeration_exhaustive` per FAI #11 | H-R3-5 |
| AC4.6 | Extend with H-R3-4 Fix Shape: interactive ack at startup; periodic re-ack every 4 hours; CI-override flag `--allow-rollback-skip-confirm` separate from `--allow-rollback`. | H-R3-4 |
| AC5.6 | Extend cross-layer test commitment from 5 to 6 tests (CL-7 added) | C-R3-1 |
| Hypothesis Prescription | Extend S1a halt-or-proceed gate language: worst-axis Wilson UB now computed across 4 adversarial axes (i/ii/iii + iv joint reconnect+concurrent) per M-R3-1. | M-R3-1 |
| Performance Benchmarks | Add: `Broker.refresh_positions()` single-flight serialization overhead ≤ 1ms p95 (lock acquisition + coalesce-window check) | C-R3-1 |
| Performance Benchmarks | Add: helper `_read_positions_post_refresh()` per-call overhead ≤ 5µs | M-R3-4 |
| Config Changes | Add footnote on `locate_suppression_seconds`: "Validator bounds (300–86400) are seconds in monotonic time per H-R3-1; equivalent to wall-clock under normal operation." | H-R3-1 |
| Config Changes | Update `pending_sell_age_watchdog_enabled` row: storage = in-memory only; auto→enabled flip is `asyncio.Lock`-guarded; restart resets to `auto`. | H-R3-2 |
| Session Count Estimate | Increase pytest target: was 88–134 effective, now 95–145 effective (~7–11 net new tests for C-R3-1 + 4 High findings) | aggregate |
| Cumulative Diff Bound | Recalibrate `argus/execution/order_manager.py` ceiling: was ~1150–1300 LOC, now ~1200–1350 LOC | aggregate |
| Cumulative Diff Bound (NEW) | Add `argus/execution/ibkr_broker.py`: ~30–50 LOC for serialization wrapper | C-R3-1 |
| Cumulative Diff Bound (NEW) | Add `argus/risk/risk_manager.py`: ~20 LOC for halt-entry Check 0 extension | H-R3-3 |
| Cumulative Diff Bound (NEW) | Add `argus/api/v1/positions.py` (NEW file): ~30 LOC for halt-clear endpoint | H-R3-3 |
| Cumulative Diff Bound (NEW) | Add `scripts/clear_position_halt.py` (NEW file): ~20 LOC for CLI tool | H-R3-3 |
| Cumulative Diff Bound (NEW) | Add `argus/main.py`: ~30 LOC for interactive ack + periodic re-ack | H-R3-4 |
| Sprint Abort Condition (NEW) | Add #N: "If Fix A serialization spike (S3b) fails AND no alternative serialization design surfaces, sprint halts; operator decides whether to escalate to Phase A re-entry retroactively." | C-R3-1 |

### 7.2 `spec-by-contradiction.md` amendments

| Section | Amendment | Source |
|---------|-----------|--------|
| Edge Case to Reject #18 | Extend: "Treating concurrent `Broker.refresh_positions()` callers as serialized at the IBKR/ib_async layer without single-flight protection. The single-flight `asyncio.Lock` + 250ms coalesce window per C-R3-1 Fix A is the structural defense; relying on ib_async's internal de-duplication is NOT sufficient because the per-caller `wait_for` correlation is unverified." | C-R3-1 |
| Edge Case to Reject #19 (NEW) | "`--allow-rollback-skip-confirm` used in production startup scripts. The flag exists for CI ONLY; production startup MUST require the interactive ack per H-R3-4 fix shape." | H-R3-4 |
| Edge Case to Reject #20 (NEW) | "Treating Branch 4 alert spam under repeated refresh-failure on the same position as expected behavior. Per M-R3-2 fix shape, Branch 4 firings on the same `ManagedPosition.id` are throttled to one per hour at alert layer." | M-R3-2 |
| Edge Case to Reject #21 (NEW) | "Treating watchdog `auto`→`enabled` flip as surviving ARGUS restart. Per H-R3-2 fix shape, the flip is in-memory only; restart resets to `auto`. Post-restart `is_reconstructed=True` posture (AC3.7) provides the structural defense for reconstructed positions; new positions are exposed until next case-A observation." | H-R3-2 |

### 7.3 `falsifiable-assumption-inventory.md` amendments

**At Phase C (now, in this amendment cycle):** add a "Pending FAI
extensions committed in `round-3-disposition.md`" subsection at the
bottom of the inventory document, listing FAI #10 + #11 with their
materialization timing (S3b + S4a-ii sprint-close respectively). The
FAI table itself stays at 9 entries until S3b/S4a-ii materialize the
new entries.

**Operator-override audit-trail anchor:** the pending-extensions
subsection makes the deferred materialization auditable from the
artifact itself, not just from the disposition document.

### 7.4 `session-breakdown.md` amendments

| Session | Amendment |
|---------|-----------|
| S3b | Add sub-spike: Fix A serialization concurrent-caller regression test (FAI #10 falsifying spike). Add LOC budget: ~30–50 LOC `ibkr_broker.py` + ~50 LOC test fixture. Re-validate compaction risk score (was 12; expected 12.5–13). |
| S4a-ii | Add: `test_bookkeeping_callsite_enumeration_exhaustive` (FAI #11 falsifying spike). LOC budget: ~40 LOC test. |
| S4a-ii | Add: AST-no-await scan extended to `_read_positions_post_refresh()` helper per M-R3-4. |
| S4b | Add: interactive ack + periodic re-ack + CI-override flag implementation per H-R3-4. LOC budget: ~30 LOC. |
| S5c | Add: CL-7 cross-layer test (concurrent AC2.5 fallbacks + broker state mutation between callers). LOC budget: ~80 LOC. |
| S2a | Add precondition check for existing `_trail_flatten` per-position serialization per M-R3-3. |

**Session count unchanged at 13.** No new sessions added; existing
sessions extended within compaction-risk budget.

### 7.5 `regression-checklist.md` amendments

| Invariant | Amendment | Source |
|-----------|-----------|--------|
| 28 (NEW) | "`Broker.refresh_positions()` body wrapped in single-flight `asyncio.Lock` + 250ms coalesce window; concurrent-caller regression test green at S3b" | C-R3-1 |
| 29 (NEW) | "Bookkeeping callsite-enumeration AST exhaustiveness test green at S4a-ii" | H-R3-5 |
| 30 (NEW) | "`refresh_positions`-then-`get_positions` sequence wrapped in `_read_positions_post_refresh()` helper; AST-no-await scan extended to helper body" | M-R3-4 |
| 31 (NEW) | "`time.monotonic()` used at all suppression timeout sites; `time.time()` regression test green at S3b" | H-R3-1 |
| 32 (NEW) | "RiskManager Check 0 extended to reject entries on positions with `halt_entry_until_operator_ack=True`; regression test green at S3b" | H-R3-3 |
| 33 (NEW) | "Interactive ack at startup when rollback active; CI-override flag separate; regression test green at S4b" | H-R3-4 |
| 34 (NEW) | "Branch 4 alert throttling: 1-hour per-position cooldown; regression test green at S3b" | M-R3-2 |

**Total invariants:** 27 (Round 2 baseline) + 7 (Round 3) = **34**.

### 7.6 `escalation-criteria.md` amendments

Add new section at top: **"Round 3 Operator Override Log Entry."**
Reproduces § 1 Operator Override Invocation of this disposition
verbatim. Provides the in-document audit-trail anchor required by
Decision 7's "explicit and logged" clause.

### 7.7 `doc-update-checklist.md` amendments

Add D-class items:
- **D15:** at sprint-close, materialize FAI #10 in `falsifiable-assumption-inventory.md`
  per S3b close-out artifact
- **D16:** at sprint-close, materialize FAI #11 per S4a-ii close-out
  artifact
- **D17:** at sprint-close, capture process-evolution lesson F.8 in
  `docs/process-evolution.md` (operator-override pattern with
  proportional in-sprint mitigation)
- **D18:** at sprint-close, log Round 3 disposition in
  `docs/sprint-history.md` Sprint 31.92 row
- **D19:** at sprint-close, append C-R3-1 + RSK-REFRESH-POSITIONS-CONCURRENT-CALLER
  + RSK-WATCHDOG-AUTO-FLIP-RESTART-LOSS to DEC-390's Cross-References
  section

---

## 8. Verification Step (Step 3 of runway)

Per `protocols/adversarial-review.md` v1.1.0 § Substantive vs Structural
decision rubric, re-evaluate whether Round 3 amendments fire enough
triggers to require a Phase B re-run.

**Reviewer prediction (operator concurs):** amendments are local
spec-text edits — AC text revisions, new test additions, helper
extractions. NO Hypothesis Prescription modifications, NO new design
choices, NO new mechanism selection. Substantive vs Structural rubric
is expected to fire 0–1 triggers (well below the 5-of-8 threshold for
Phase B re-run).

**Compaction-risk re-validation per session:** verify all 13 sessions
remain ≤13.5 post-amendment. S3b is the highest-risk delta (sub-spike
+ Fix A implementation + concurrent-caller regression). Baseline S3b
score was 12; post-amendment expected 12.5–13. S5c also impacted
(CL-7 added); baseline was 11, post-amendment expected 11.5.

If either check fails, kick back to spec amendment cycle for re-scoping.

---

## 9. Phase D Readiness

Upon completion of:
- Step 1 (this disposition) ✓
- Step 2 (spec amendment cycle producing surgical edits per § 7
  manifest)
- Step 3 (Substantive vs Structural rubric re-check + compaction-risk
  re-validation)

...the sprint planner proceeds to Phase D — implementation prompts
generated for S1a / S1b / S2a / S2b / S3a / S3b / S4a-i / S4a-ii / S4b /
S5a / S5b / S5c. The mid-sprint Tier 3 review (M-R2-5) inserts between
S4a-ii and S4b per Round 2 disposition + Round 3 reinforcement (M-R2-5
is the proportional re-review for the C-R3-1 Fix A).

S1a + S1b spike sessions run first; spike outputs gate operator
mechanism-selection confirmation; S2a/S2b/S3a/S3b implementation
prompts generated post-confirmation. This is the natural pause point
in the sprint flow.

---

## 10. Process-Evolution Lesson F.8 (NEW, materialized at sprint-close)

> **F.8 (2026-04-29, Sprint 31.92 Round 3 disposition):** When the
> FAI's self-falsifiability clause fires for a borderline-class finding
> with a mechanically-simple fix, operator override per Decision 7 (b)
> with committed-in-sprint mitigation is a proportional response. The
> pattern is bounded: not every primitive-semantics finding warrants
> the full ceremonial response of Phase A re-entry. The mid-sprint
> Tier 3 review provides the structured re-review at proportional cost.
>
> **Pattern recognition criteria for operator override:**
> 1. Reviewer's confidence on FAI-class designation is "moderate" or
>    "borderline" (not "high").
> 2. The proposed fix is mechanically simple (≤100 LOC, well-understood
>    concurrency/correctness pattern).
> 3. A mid-sprint Tier 3 review is already scheduled and can absorb the
>    structured re-review of the fix.
> 4. The marginal value of full Phase A re-entry's design exploration
>    is low (the fix shape is settled; what's needed is implementation +
>    verification).
>
> **Pattern anti-recognition criteria (when operator override is NOT
> appropriate):**
> 1. Reviewer's confidence on FAI-class designation is "high" with no
>    borderline aspect.
> 2. The proposed fix requires structural redesign or new mechanism
>    choice.
> 3. No mid-sprint Tier 3 review is scheduled.
> 4. The finding is the Nth instance of a recurring pattern within the
>    same sprint (e.g., 3+ operator overrides in one sprint suggests
>    the FAI process itself is not catching the right things).

---

## End of disposition

**Phase C Round 3 disposition SEALED.** Step 2 (spec amendment cycle)
unblocked. Operator opens fresh Claude.ai conversation with the Round 3
verdict + this disposition + current Phase C artifact set + the
amendment manifest in § 7. Prompt: *"Apply the Round 3 disposition's
spec-text amendments to all Phase C artifacts per the § 7 manifest.
This is a surgical edit pass, not a re-design — the dispositions are
settled. Produce the amended artifacts plus a manifest of what changed
where."*
