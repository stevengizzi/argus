# Sprint 31.92: Sprint-Level Escalation Criteria

> **Phase C artifact 5/8.** Specific, evaluable trigger conditions that halt
> the sprint and require operator + reviewer attention before proceeding.
> Embedded into every implementation prompt so the implementer knows when to
> halt rather than push through. CRITICAL safety sprint — bias toward halt
> over push-through; the cost of a missed halt is a regression of the same
> mechanism class that already empirically falsified DEC-386 once.

## Trigger Conditions (Halt Conditions)

Each row below specifies a concrete trigger and the required response. If ANY
trigger fires, the implementer halts the session, posts to the work-journal
conversation, and waits for operator + reviewer disposition before proceeding.

### A. Mandatory Halts (Tier 3 architectural review automatically fires)

| # | Trigger | Required Response |
|---|---------|-------------------|
| A1 | **Spike S1a returns `status: INCONCLUSIVE`** in `scripts/spike-results/spike-def204-round2-path1-results.json` (i.e., findings fall outside H1/H2/H4 from Sprint Spec §"Hypothesis Prescription"). | Halt before S2a impl. Operator arranges Tier 3 review of the alternative mechanism (e.g., a hypothesis the spec author did not enumerate). The S2a/S2b implementation prompts MUST NOT be generated until Tier 3 selects a mechanism. Per protocol §"Hypothesis Prescription": "Do NOT ship a Phase B fix that doesn't address the Phase A finding." |
| A2 | **Spike S1b returns `status: INCONCLUSIVE`** in `scripts/spike-results/spike-def204-round2-path2-results.json` (e.g., locate-rejection error string varies non-deterministically across trials, OR no held-pending-borrow release ever observed in spike trials). | Halt before S3a impl. Tier 3 reviews whether to (a) broaden the fingerprint to a regex/list, (b) make `locate_suppression_seconds` operator-configurable per-symbol, or (c) accept that the suppression-timeout fallback (AC2.5) is the dominant code path and re-prioritize accordingly. |
| A3 | **Composite validation S5b produces `phantom_shorts_observed > 0`** OR `total_sold_le_total_bought: false` in any synthetic scenario. | Halt sprint. Do NOT seal. The mechanism closure is empirically falsified; this is the same failure class that ended Sprint 31.91's `~98%` claim. Tier 3 reviews which session's coverage was insufficient and what new mechanism path the validation surfaced. |
| A4 | **Any session's diff modifies a DEC-385/386/388 surface listed in the SbC "Do NOT modify" list** beyond the explicit byte-for-byte preservation OR explicit additive points (POLICY_TABLE entry for sell_ceiling_violation; cancel-and-await consumer at AC1; locate-rejection consumer at AC2.3; ceiling guard at AC3.2). | Halt. RULE-004 + SbC violation. Revert the unintended change. If the change is necessary (e.g., the chosen mechanism cannot be implemented without modifying a protected surface), escalate — Tier 3 reviews whether the SbC needs amendment OR whether the mechanism itself was wrong. |
| A5 | **DEF-158 retry 3-branch side-check structure is modified** (i.e., a 4th branch is added to `_check_flatten_pending_timeouts` lines ~3424–3489 instead of the spec-prescribed upstream-at-`place_order` detection). | Halt. SbC §"Edge Cases to Reject" #13 violation. The 3-branch side-check (BUY → resubmit / SELL → alert+halt / unknown → halt) is preserved verbatim; Path #2 detection MUST be at the `place_order` exception in the 4 SELL emit sites. Tier 3 reviews whether the design rationale for this separation needs to change. |
| A6 | **Any Tier 2 review on any session produces verdict = CONCERNS or ESCALATE.** | Halt. Operator + Tier 2 reviewer disposition the finding before next session begins. CONCERNS → typically iterate within the same session. ESCALATE → operator decides whether to revert the session's commit or fix forward. |
| A7 | **First post-merge paper session (i.e., the first paper session run AFTER S5b seal) shows ANY new phantom shorts** (vs zero expected for the post-fix state). | Halt sprint. Revert the most recently merged sessions on `main` if specific session(s) can be identified; otherwise revert to pre-S2a HEAD. Tier 3 architectural review of why the validation-layer assertions in S5a + S5b did not catch the regression. Re-plan the session(s) (likely with new tests added) before re-attempting. **This is the same failure mode that ended DEC-386's `~98%` claim**; the response must be at least as rigorous. |
| A8 | **AC4 ceiling implementation reveals architectural conflict with DEC-369 broker-confirmed reconciliation immunity** — specifically, `reconstruct_from_broker`-derived positions cannot correctly initialize `cumulative_sold_shares` because the broker query at startup does not preserve fill-history. | Halt at S4a mid-implementation. Tier 3 evaluates whether to (a) initialize broker-confirmed positions to `cumulative_sold_shares = 0` AND `shares_total = abs(broker_position.shares)` (the spec's intent — accept the loss of historical accounting on broker-confirmed positions), (b) defer ceiling enforcement on broker-confirmed positions until DEF-209 lands (Sprint 35+ Learning Loop V2), or (c) some third option. SbC §"Adversarial Review Reference" item #5 explicitly flagged this as a scrutiny target. |
| A9 | **Path #1 spike S1a measures `cancel_all_orders(symbol, await_propagation=True)` p95 latency >500ms** OR observes ≥2 trials where propagation never converged within 5s. | Halt before S2a (under H1 path). Tier 3 evaluates whether the H1 cost-of-correctness exceeds an acceptable bound. If H2 (amend-stop-price) measured cleanly in S1a, switch fix shape to H2. If neither H1 nor H2 measured cleanly, Tier 3 evaluates a deeper architectural question: does ARGUS need to suspend Sprint 31.92 in favor of Sprint 31.94 reconnect-recovery first (which may be the structural cause of the broker latency drift)? |
| A10 | **Path #1 spike S1a OR S2a regression test reveals that the chosen mechanism (cancel-and-await OR amend) breaks DEC-117 atomic-bracket invariants** (parent-fails-children-cancel pattern OR transmit-flag semantics OR child-OCA-group preservation). | Halt. The do-not-modify boundary on DEC-117 was crossed. Operator decides whether to refine the mechanism approach to preserve DEC-117 OR accept a DEC-117 amendment — the latter requires Tier 3 + adversarial-review re-run. |
| A11 | **AC4 SELL-volume ceiling produces a false-positive in production paper trading** post-merge (i.e., a legitimate SELL is refused because `cumulative_sold_shares + requested_qty > shares_total` due to fill-callback ordering or partial-fill aggregation defect). | Halt. RSK-CEILING-FALSE-POSITIVE materialized. Tier 3 reviews whether to (a) tighten fill-callback aggregation in `on_fill` (adds complexity to a hot path), (b) introduce a small tolerance epsilon (defeats the safety property), or (c) revert ceiling enforcement until the underlying fill-aggregation bug is independently fixed. **Default: option (a) with a regression test** — option (b) is REJECTED at spec-time. |
| A12 | **Any session's diff touches `argus/main.py::check_startup_position_invariant`, `_startup_flatten_disabled`, or `argus/execution/order_manager.py::reconstruct_from_broker`** (Sprint 31.94 D1+D2 surfaces). | Halt. SbC §"Do NOT modify" violation. These surfaces are time-bounded by Sprint 31.94 per RSK-DEC-386-DOCSTRING. Modification here would couple Sprint 31.92 and 31.94 dependencies and re-introduce the architectural sequencing problem the renumbering resolved. |
| A13 | **Spike artifact `scripts/spike-results/spike-def204-round2-path{1,2}-results.json` is older than 30 days at the time of the FIRST post-merge paper session**, or `ib_async`/IBKR Gateway has been upgraded between spike-run and paper-session. | Halt the post-merge paper session. Operator re-runs both spikes. If both return prior status: proceed with paper session. If S1a or S1b status changes (e.g., locate-rejection string drifted): the closure is invalidated; halt sprint, re-plan affected sessions. (Mirror of DEC-386's `PATH_1_SAFE` 30-day re-validation discipline.) |
| A14 | **Adversarial review (Phase C-1) produces ≥1 Critical finding.** | Halt prompt generation. Return to Phase A for revisions per protocol §"Phase C-1 Adversarial Review Gate". Re-author Sprint Spec / Spec by Contradiction / Session Breakdown / this Escalation Criteria as needed. Generate Revision Rationale document. Re-run adversarial review on the post-revision package before proceeding to Phase D. |

### B. Mandatory Halts (Tier 3 not required, but operator + Tier 2 reviewer must disposition)

| # | Trigger | Required Response |
|---|---------|-------------------|
| B1 | **Pre-existing flake count increases.** Specifically: any of DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 fail more frequently than baseline OR a NEW intermittent failure appears that doesn't have a DEF entry yet (RULE-041). | Halt. File DEF entry with symptom + repro hint + xdist worker context. Operator decides whether to fix in this sprint or defer. |
| B2 | **Test count goes DOWN** (regression: existing tests deleted or skipped without explanation). | Halt. RULE-019 violation. Implementer explains in close-out which tests were deleted and why; operator + Tier 2 reviewer assess. |
| B3 | **Pytest baseline ends below 5,269** at the close-out of any session. | Halt. The new tests are additive; existing baseline must hold. Investigate which test broke and either fix or revert. |
| B4 | **CI fails on the session's final commit and the failure is NOT a documented pre-existing flake.** | Halt per RULE-050. Do not proceed to next session until CI green is achieved. RULE-052: if CI is red for a known-cosmetic reason, log that assumption explicitly at each subsequent commit. |
| B5 | **Structural anchor (function name / class name / regex pattern) referenced in impl prompt does not match repo state during pre-flight grep-verify.** | Halt mid-pre-flight. Re-anchor the session's surgical edits against actual current structural anchors. RULE-038 grep-verify discipline. Mark the finding as RESOLVED-VERIFIED if change is already in place, or flag the discrepancy in the close-out. **Note:** absolute line numbers cited in the prompt are "directional only" per protocol v1.2.0; the structural anchor is what binds. |
| B6 | **A do-not-modify-list file appears in the session's `git diff`.** | Halt. RULE-004 violation. Revert the unintended change before close-out. If the change is necessary, escalate to operator (the do-not-modify list itself needs amendment, OR the spec needs revision). |
| B7 | **Test runtime degrades >2× from baseline** (full suite or scoped) OR a single test's runtime exceeds 60 seconds. | Halt and investigate. Per RULE-037, verify no orphaned background processes are inflating runtime. May be a pyarrow/xdist (DEF-190) recurrence; document in close-out. Path #1 cancel-and-await fixtures could plausibly add latency to existing trail-flatten tests; benchmark and decide whether to mock the propagation. |
| B8 | **Any session's diff modifies `frontend/`** OR Vitest count changes from baseline 913. | Halt. SbC §"Do NOT modify" #5 violation. Sprint 31.92 has zero frontend scope. Revert. |
| B9 | **Path #2 spike S1b's hold-pending-borrow release window p99 measurement exceeds the default `locate_suppression_seconds = 300s`** but still bounded (e.g., p99 = 480s). | Halt at S3a impl. Operator + Tier 2 disposition: raise the default to a measurement-driven value (e.g., p99 + 20% margin → 600s), OR accept that the suppression-timeout fallback alert (AC2.5) is the dominant code path with a note in DEC-390. |
| B10 | **Any new pytest test exceeds 5s individual runtime** at S5a or S5b (the validation sessions). | Halt and investigate. Path #1/#2 validation fixtures may have slow synthetic-clock loops or unmocked propagation. Reduce fixture scope OR mock the slow path; do NOT carry slow tests into the final suite. |
| B11 | **Implementer's grep-verify reveals more or fewer occurrences of `_OCA_TYPE_BRACKET` in `argus/execution/order_manager.py` than the 4 specified in S4b's spec** (i.e., line numbers ~3212, ~3601, ~3714, ~3822 + the constant declaration at ~105). | Halt at S4b. The constant has been used in additional sites since DEC-386 S1b landed; OR the SbC over-counted; OR the file structure has drifted. Re-anchor and proceed only after operator confirms the actual occurrence count matches the intended replacement scope. |

### C. Soft Halts (Continue with extra caution + close-out flag)

| # | Trigger | Required Response |
|---|---------|-------------------|
| C1 | **Implementer notices a bug or improvement opportunity OUTSIDE the current session's scope.** | Document in close-out under "Deferred Items" (RULE-007). Do NOT fix in this session. The maximum-overlap zone (`order_manager.py` touched by 6 of 10 sessions) makes scope discipline load-bearing. |
| C2 | **First fix attempt fails and a second approach emerges.** | Per RULE-008, allow ONE additional approach attempt without operator approval; if that also fails, halt and request guidance. |
| C3 | **Two failed fix attempts on the same bug.** | Switch to diagnostic-first mode (RULE-030). Build a minimal repro outside the application code. Close-out marks Context State YELLOW. |
| C4 | **Context State trending YELLOW** (long conversation, many file reads, many edits). | Per RULE-027, proactively checkpoint: commit, run scoped tests, produce partial close-out, suggest continuing in a fresh session. The 6-of-10-sessions overlap on `order_manager.py` (4,421 lines) means context budget is tight. |
| C5 | **Implementer is uncertain whether a change crosses the do-not-modify boundary** (e.g., a refactor that touches `order_manager.py` near but not in a protected line range). | Pause; consult the SbC do-not-modify list explicitly; if still uncertain, escalate to operator before making the change. Better to halt than to silently regress. |
| C6 | **Phase A's grep-verified line numbers drift 1–5 lines from spec.** | Continue (small drift is RULE-038-acknowledged); document the actual line numbers in the close-out for the next session's reference. Per protocol v1.2.0, structural anchors bind, not line numbers. |
| C7 | **A test layer's grep regression guard (e.g., S4b's "no `_OCA_TYPE_BRACKET` constant") false-positives on a legitimate site** (e.g., a docstring referencing the prior constant name for historical context). | Add an explicit `# OCA-EXEMPT: <reason>` comment OR use a more specific regex. Document in close-out. Do NOT remove the regression guard. |
| C8 | **S1a/S1b spike output JSON schema does not exactly match the schema specified in the spec** (e.g., field names differ slightly because the operator-developer revised them during the spike). | Continue. Document the actual schema in the close-out. The downstream impl prompts at S2a/S2b/S3a/S3b consume the JSON; minor schema deviations are acceptable as long as the gating fields (`status`, `path1_mechanism`, exact fingerprint string) are present and meaningful. |
| C9 | **AC3.4 "per-managed-position ceiling" test reveals that two ManagedPositions on same symbol DO interact in some unexpected way** (e.g., one position's `cumulative_sold_shares` increment fires on the wrong fill due to order-id collision). | Halt the AC3.4 test, investigate. If the interaction is a pre-existing OrderManager bug surfaced by the new field, file a DEF and decide scope (fix in S4a or defer). If the interaction is introduced by AC3.1 increment logic, fix in S4a. |

## Escalation Targets

For each halt, the escalation flows as follows:

- **Code-level questions** (does this approach work?): Tier 2 reviewer (the
  `@reviewer` subagent in the same session) is first-line; operator is second-line.
- **Spec-level questions** (does this still match the Sprint Spec?):
  Operator + sprint-planning conversation are required.
- **Architectural questions** (does this change a DEC?): Tier 3 reviewer in a
  separate Claude.ai conversation, with operator dispositioning the verdict.
- **Safety questions** (does this risk paper-trading regressions or live
  trading consideration?): Operator + Tier 3 reviewer; pause paper trading if
  in doubt.

## Sprint Abort Conditions

The sprint as a whole is aborted (not just an individual session) if ANY of:

1. **Two or more A-class halts within the same week.** Indicates the spec or
   the underlying mechanism understanding is wrong; the sprint needs replanning.
   Sprint 31.91 had two Tier 3 reviews + two in-sprint hotfixes; that pattern
   is a sprint-stretch-but-acceptable outcome. **Three or more A-class halts**
   crosses into replanning territory.

2. **Mechanism turns out to be different from S1a/S1b spike findings**
   (DEBUNKED status). E.g., a paper session shows phantom shorts traceable to
   a third path (Path #3) not enumerated by Phase A. RULE-051 (mechanism-
   signature-vs-symptom-aggregate) — investigate whether the spike's
   characterization was incomplete OR whether the Apr 28 debrief itself missed
   a third mechanism. Pivot to a Sprint 31.92.5 or 31.93-prefix sprint with
   new diagnostic before continuing.

3. **Three failed paper sessions post-S5b seal** — i.e., DEF-204 mechanism
   keeps firing despite the architectural closure landed. Would mean DEC-390
   itself was wrong, similar to DEC-386's empirical falsification on
   2026-04-28. The decision-log entry would be marked SUPERSEDED-BY-NEXT-DEC,
   and a new diagnostic phase opens. **This abort condition's existence is
   itself evidence-based design** — we have learned from Sprint 31.91 that
   architectural closures need empirical falsification, not just test-suite
   green.

4. **Phase 0 housekeeping invalidated** — i.e., a parallel sprint or impromptu
   has renumbered or renamed Sprint 31.93/31.94/31.95 in a way that conflicts
   with Sprint 31.92's cross-references in DEF-208/211/212/215 routing
   columns. Halt; reconcile cross-references; re-issue Phase 0 patch before
   resuming Phase D. (Low likelihood; flagged for completeness.)

5. **Live trading enabled mid-sprint** by operator decision (without sprint
   completion). **Sprint Spec §"Out of Scope" item 16** explicitly defers
   live-trading enablement; sprint must complete in paper before any live
   transition consideration. If operator decides to transition early
   regardless, sprint is paused (not aborted) until the transition is reverted
   OR sprint is rebaselined for the new context.

6. **DEC-390 cannot be coherently materialized at sprint-close** — e.g., the
   four layers (Path #1 + Path #2 + ceiling + DEF-212 rider) end up addressing
   different mechanisms than spec-anticipated, OR adversarial review reveals
   an architectural conflict between L1 and L3 that requires splitting DEC-390
   into multiple DECs. **Default disposition: split the DEC and proceed with
   sprint-close** — this is not a sprint-abort trigger but a doc-sync
   complication. Listed here for completeness.

## Closing the Sprint

The sprint may be sealed (D14 sprint-close doc-sync) only when ALL of:

- All 10 sessions have Tier 2 verdict CLEAR (or CONCERNS dispositioned to CLEAR via re-iteration).
- S5a's `sprint-31.92-validation-path1.json` artifact committed to `main` with `path1_safe: true`.
- S5b's `sprint-31.92-validation-path2.json` artifact committed to `main` with `path2_suppression_works: true`.
- S5b's composite Pytest test (`test_composite_validation_zero_phantom_shorts_under_load`) green.
- Full suite green at S5b close-out (DEC-328 final-review tier; full suite mandatory).
- DEC-390 written below in `docs/decision-log.md` with all 4 layers and complete cross-references.
- DEF-204 row in `CLAUDE.md` marked **RESOLVED-PENDING-PAPER-VALIDATION** (NOT RESOLVED — per SbC §"Edge Cases to Reject" #14).
- DEF-212 row in `CLAUDE.md` marked **RESOLVED**.
- `docs/dec-index.md` updated with DEC-390 entry.
- `docs/sprint-history.md` row added.
- `docs/roadmap.md` updated per `doc-update-checklist.md`.
- Cessation criterion #5 counter explicitly RESET to 0/5 for the new post-Sprint-31.92 paper-session window. (Sprint 31.91's prior #5 counter is supersumed.)