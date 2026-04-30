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
