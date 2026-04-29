# Sprint 31.92: What This Sprint Does NOT Do

> **Revision history:** Round 1 authored 2026-04-28; Round-1-revised 2026-04-29 incorporating adversarial findings C-1 (Edge Case #1 was structurally wrong about asyncio serialization), C-2 (new Out of Scope item rejecting reviewer's `data/argus.db` reconstruction option), H-1 (new Edge Case rejecting ceiling check at bracket placement), H-3 (Edge Case #5 updated to reflect broker-verification mitigation). See `revision-rationale.md` for the verdict-to-disposition trace.

This document defines the boundaries of Sprint 31.92 — DEF-204 Round 2. It exists to prevent scope creep during implementation and to give the adversarial reviewer (Phase C-1 Round 2) and Tier 2 reviewer (per-session) clear boundaries to check. Sprint 31.91 Tier 3 #1 explicitly flagged scope creep as a concern; this document is the structural defense against that pattern recurring.

The sprint focuses narrowly on closing the two empirically-falsifying paths from the 2026-04-28 paper-session debrief, plus a structural ceiling with concurrency-safe pending reservation as defense-in-depth, plus the DEF-212 rider. Everything else — even items thematically adjacent to safety, reconciliation, or order-management hygiene — is explicitly out of scope.

---

## Out of Scope

These items are related to the sprint goal but are explicitly excluded:

1. **Structural refactor of `_flatten_position`, `_trail_flatten`, `_escalation_update_stop`, or `_check_flatten_pending_timeouts` beyond the explicit safety properties enumerated in AC1–AC4.** These four functions are touched by 6 of the 10 sessions (S2a/S2b/S3a/S3b/S4a + S4b indirectly via construction surface) — that's a maximum-overlap zone. The temptation to "while I'm in there, also fix X" must be resisted. Structural cleanup is Sprint 31.93 component-ownership scope.

2. **Modifications to DEC-386's 4-layer OCA architecture (Sessions 0/1a/1b/1c).** Specifically: `Broker.cancel_all_orders(symbol, *, await_propagation)` ABC contract, `IBKRBroker.place_bracket_order` OCA threading, `ManagedPosition.oca_group_id`, `_handle_oca_already_filled`, `# OCA-EXEMPT:` exemption mechanism, `reconstruct_from_broker()` STARTUP-ONLY docstring. All preserved byte-for-byte (regression invariant R6). Sprint 31.92 ADDS to this architecture (amend-stop-price OR cancel-and-await on Path #1; pending+sold ceiling on AC4); it does NOT modify the existing layers. The existing `bracket_oca_type=0` rollback escape hatch is PRESERVED — Sprint 31.92 does NOT remove the rollback option, only adds a startup warning per AC4.6 when the operator deliberately enables it.

3. **Modifications to DEC-385's 6-layer side-aware reconciliation contract.** Specifically: `reconcile_positions()` Pass 1 startup branch + Pass 2 EOD branch, `phantom_short_gated_symbols` audit table, DEF-158 retry 3-branch side-check, `phantom_short_retry_blocked` alert path. Path #2's broker-verified suppression-timeout fallback REUSES the existing `phantom_short_retry_blocked` alert type — it does NOT introduce new behavior in DEC-385's surfaces.

4. **Relocation of `_is_oca_already_filled_error` from `argus/execution/ibkr_broker.py` to `argus/execution/broker.py`.** Tier 3 #1 Concern A (Sprint 31.91, 2026-04-27) called for this relocation. Phase A explicitly DEFERRED it to Sprint 31.93 component-ownership because (a) `broker.py` ABC modification is the natural home, (b) Sprint 31.92 already has 6 sessions touching `order_manager.py` and adding `broker.py` to the modify list expands blast radius unnecessarily, (c) the helper's current location is functionally correct — the relocation is cosmetic.

5. **DEF-211 D1+D2+D3 (Sprint 31.94 sprint-gating items).** Specifically: `ReconstructContext` enum + parameter threading on `reconstruct_from_broker()`, IMPROMPTU-04 startup invariant gate refactor, boot-time adoption-vs-flatten policy decision for broker-only LONG positions. RSK-DEC-386-DOCSTRING bound stays bound by Sprint 31.94. Sprint 31.92 must NOT touch `argus/main.py:1081` (the `reconstruct_from_broker()` call site) or `check_startup_position_invariant()`. The new `ManagedPosition.is_reconstructed: bool` flag (AC3.7) is set inside `reconstruct_from_broker()` itself — that single-line change inside the function body is in scope; the call site and surrounding `argus/main.py` infrastructure remain untouched.

6. **DEF-194/195/196 reconnect-recovery work (Sprint 31.94).** Specifically: IBKR `ib_async` stale position cache after reconnect, `max_concurrent_positions` divergence after disconnect-recovery, DEC-372 stop-retry-exhaustion cascade events. The 38 "Stop retry failed → Emergency flattening" events on Apr 28 are a Path #1 surface (covered by AC1.3's `_resubmit_stop_with_retry` emergency-flatten branch); the cluster-wide reconnect-recovery analysis is NOT in scope. **Specifically out: `IBKRReconnectedEvent` consumer that clears the locate-suppression dict.** That coupling is deferred to Sprint 31.94 when the producer lands. AC2.5's broker-verification-at-timeout fallback is the structural mitigation Sprint 31.92 ships in lieu of the consumer.

7. **`evaluation.db` 22GB bloat or VACUUM-on-startup behavior.** Sprint 31.915 already merged DEC-389 retention + VACUUM. The Apr 28 debrief's secondary finding (eval.db forced premature shutdown) is closed.

8. **`ibkr_close_all_positions.py` post-run verification feature.** The Apr 28 debrief flagged this as a HIGH-severity DEF-231 candidate. Phase A retracted it: operator confirmed 2026-04-29 that the 43 pre-existing shorts at boot were missed-run human error, NOT a script defect. The script does its job when run; building a verification harness around operator hygiene would not have caught the human-error case. NOT this sprint.

9. **The 4,700 broker-overflow routings noted in the Apr 28 debrief.** Debrief explicitly defers: "Possibly fine; possibly indicates `max_concurrent_positions` is too tight for the actual signal volume." Requires a separate analysis pass against `max_concurrent_positions: 50` sizing. NOT a safety defect; out of scope.

10. **DEF-215 reconciliation-WARNING throttling.** Already DEFERRED with sharp revisit trigger ("≥10 consecutive cycles AFTER Sprint 31.91 has been sealed for ≥5 paper sessions"). Sprint 31.92 closure does not satisfy the trigger; DEF-215 stays deferred.

11. **Sprint 31B Research Console / Variant Factory work.** Conceptually adjacent but functionally orthogonal. Sequenced after 31.92 per Phase 0 routing.

12. **Sprint 31.95 Alpaca retirement (DEF-178/183).** Wholly orthogonal scope.

13. **New alert observability features beyond a single `POLICY_TABLE` entry for `sell_ceiling_violation`.** Specifically out: `AlertBanner` UX changes, `AlertToastStack` queue capacity adjustments, new REST endpoints, new WebSocket event types, additional per-alert audit-trail enrichment. AC3.9 ADDS a single `POLICY_TABLE` entry (`operator_ack_required=True`, `auto_resolution_predicate=None`) and updates the AST exhaustiveness regression guard — that's the entire alert-system delta.

14. **Performance optimization beyond the explicit benchmarks in the Sprint Spec §"Performance Benchmarks".** AC's measure ≤50ms p95 amend latency (H2), ≤200ms p95 cancel-and-await (H1 fallback), ≤10µs ceiling check, ≤5µs locate-suppression check, ≤200ms p95 broker-verification at timeout, ≤1µs pending reservation arithmetic, ≤45s suite runtime regression. If any actual measurement exceeds these targets, halt and surface — do NOT optimize speculatively.

15. **Backporting AC1/AC2/AC3/AC4 fixes to Sprint 31.91-tagged code.** Sprint 31.92 lands at HEAD post-31.91-seal. There is no scenario where 31.92's mechanism would be backported separately.

16. **Live trading enablement.** Sprint 31.91's cessation criterion #5 (5 paper sessions clean post-seal) reset on Apr 28. Sprint 31.92's seal STARTS a new 5-session counter. Live trading remains gated by that counter PLUS Sprint 31.91 §D7's pre-live paper stress test under live-config simulation (DEF-208 — separately scoped).

17. **Documentation rewrites of `docs/architecture.md` §3.7 Order Manager beyond what AC's require.** AC-required: short subsection or paragraph about (a) Path #1 mechanism (H2 amend-stop-price default, H4 hybrid fallback, H1 last-resort), (b) `_is_locate_rejection` + position-keyed suppression dict + broker-verified timeout fallback, (c) `cumulative_pending_sell_shares` + `cumulative_sold_shares` + `is_reconstructed` ceiling, (d) `bracket_oca_type` flow from config to `OrderManager.__init__` + startup warning when ≠ 1. Anything beyond these four items is OUT.

18. **Restructuring or extending `SimulatedBroker` semantically.** S5a + S5b validation scripts may add NEW test fixtures (e.g., `SimulatedBrokerWithLocateRejection`, `SimulatedBrokerWithRestartReplay`) but must not modify SimulatedBroker's existing fill-model semantics, immediate-fill behavior, or OCA simulation. Existing tests pass without modification.

19. **Sprint-close cessation-criterion celebration.** Sprint 31.92 sealing satisfies cessation criterion #4 (sprint sealed) for the new criterion-#5 counter — but criterion #5 itself (5 paper sessions clean post-Sprint-31.92 seal) starts at 0/5 again. Operator daily-flatten mitigation continues.

20. **Reading `data/argus.db` trades table on startup to reconstruct `cumulative_sold_shares` for reconstructed positions.** Round-1 reviewer's proposed option (a) for C-2. **REJECTED in Round-1 disposition** because attribution of historical SELLs to specific reconstructed positions is ambiguous when there have been multiple sequential entries on the same symbol within a session — the trades table doesn't carry `ManagedPosition.id` linkage in a form that survives restart. The conservative `is_reconstructed = True` refusal posture (AC3.7) was chosen instead. Listed here so adversarial Round 2 reviewer sees the explicit rejection rationale rather than re-litigating.

21. **Persisting `cumulative_pending_sell_shares` or `cumulative_sold_shares` to SQLite (pulling DEF-209 forward).** Round-1 reviewer's proposed option (b) for C-2. REJECTED — DEF-209 is a Sprint 35+ Learning Loop V2 prerequisite covering broader field persistence (`Position.side`, `redundant_exit_observed`, and now the ceiling counters). Pulling forward couples Sprint 31.92 to a 10+ sprint horizon. The `is_reconstructed` refusal posture removes the need for these counters to survive restart on reconstructed positions specifically.

22. **`bracket_oca_type` Pydantic validator restriction to literal `1`.** Round-1 reviewer's proposed option (a) for H-4. REJECTED — DEC-386 explicitly designed the `bracket_oca_type=0` rollback escape hatch for emergency operator response. Removing the runtime-flippability would supersede DEC-386's design intent, which is out of Sprint 31.92's prerogative. The startup CRITICAL warning per AC4.6 + `live-operations.md` documentation is the chosen mitigation.

23. **Re-running adversarial review on the original Round-1 spec.** Round 1 produced verdict Outcome B (3 Critical findings); revisions applied per `revision-rationale.md`. Round 2 reviews the REVISED package with narrower scope (validate the fixes, not the original design). NOT re-running Round 1 from scratch.

---

## Edge Cases to Reject

The implementation should NOT handle these cases in this sprint:

1. **Two or more coroutines on the same `ManagedPosition` racing through the ceiling check between place-time and fill-time.** **REVISED per Round-1 finding C-1:** asyncio's single-threaded event loop does NOT serialize emit-time concurrency — coroutines yield control during `await place_order(...)` and a second coroutine can run the entire ceiling-check-and-place sequence in the gap. This race IS a real failure mode and IS structurally addressed by AC3.1's `cumulative_pending_sell_shares` reservation pattern: the increment happens synchronously BEFORE the `await`, so the second coroutine's ceiling check sees the reservation. **Expected behavior:** the second coroutine's `_check_sell_ceiling` returns False; the second SELL is refused; alert emitted per AC3.3. Asserted by AC3.5 race test. The original Round-1 SbC framing of this case as "asyncio prevents this" was structurally wrong and has been corrected.

2. **IBKR returning a `modifyOrder` rejection during Path #1 H2 for reasons other than "stop price invalid" (e.g., 201 margin rejection, transmit-flag conflict).** Out of scope. If S1a spike confirms H2, the impl assumes amend rejections are rare AND non-deterministic ones are caught by AC1.2's regression test (mock `IBKRBroker.modify_order` to raise; assert fall-through to H4 hybrid OR halt with operator escalation). Production-side robustness for unusual amend rejections is post-revenue concern; if rejection rate exceeds 5%, mechanism shifts to H4 hybrid per Hypothesis Prescription.

3. **`cumulative_pending_sell_shares` or `cumulative_sold_shares` integer overflow.** A `ManagedPosition` that pending-or-sold > 2³¹ shares is architecturally infeasible (max position size is bounded by Risk Manager checks at single-share scale). Use `int`, not `int64` or `Decimal`. No overflow regression test.

4. **Operator manually placing SELL orders at IBKR outside ARGUS during a session.** Sprint 30 short-selling territory; reconciliation surface (DEC-385) catches the resulting state mismatch. AC4 ceiling applies to ARGUS-emitted SELLs only — manual operator actions are not in `_check_sell_ceiling`'s purview. Reconstructed positions specifically expect operator-manual flatten via `scripts/ibkr_close_all_positions.py` per AC3.7.

5. **Mid-session reconnect race with locate-suppression dict.** **REVISED per Round-1 finding H-3:** if IBKR Gateway disconnects and reconnects mid-session, existing held orders are invalidated (DEF-194/195/196 cluster, Sprint 31.94). The locate-suppression dict in Sprint 31.92 does NOT account for reconnect events explicitly (no `IBKRReconnectedEvent` consumer until Sprint 31.94 — producer doesn't exist yet). However, AC2.5's broker-verification-at-timeout fallback ELIMINATES the false-positive alert class even when stale dict entries persist post-reconnect: when the timeout fires, the broker is queried for actual position state and (if expected-long observed) the alert is suppressed and dict entry cleared. Stale dict entries during the suppression window cause additional SELLs at the same `ManagedPosition` to be skipped — for the suppression-window duration, this is conservative-but-correct (the position will close via subsequent flatten-resubmit timeout via DEF-158's retry path, OR via the suppression-timeout broker-verification fallback). Reconnect-event coupling stays deferred to Sprint 31.94.

6. **Locate-rejection error string variants ("not available for short" without the "contract is" prefix; "no inventory available"; non-English locales).** S1b spike captures the exact current string `"contract is not available for short sale"` against ≥5 hard-to-borrow microcap symbols × ≥10 trials per symbol; AC2.1's substring fingerprint matches that exact substring (case-insensitive). Variants are caught by H5's "rules-out-if" condition at S1b. If S1b finds a variant, regex pattern is broadened at S3a. If S1b is conclusive (single string), do NOT speculatively broaden — fingerprint regression test fails noisy if string drifts.

7. **`_check_sell_ceiling` violation IN PRODUCTION-LIVE-MODE configurable to "warn-only" rather than "refuse SELL".** AC3.8 defaults `long_only_sell_ceiling_enabled = true` — fail-closed. The flag exists for explicit operator override during emergency rollback ONLY. There is NO third state ("warn-only"). Booleans only.

8. **Per-`ManagedPosition` SELL ceiling with cross-position aggregation across same symbol.** AC3.4 explicitly: per-`ManagedPosition`, NOT per-symbol. If two ManagedPositions on AAPL exist (sequential entries within the morning window), each has its own ceiling. Cross-position aggregation is the existing Risk Manager max-single-stock-exposure check at the entry layer (DEC-027), which is OUT of scope to modify here.

9. **Suppression-window expiration emits more than one alert per `ManagedPosition` per session.** AC2.5: when suppression expires AND broker-verification shows unexpected state, the next SELL emit at that position publishes ONE `phantom_short_retry_blocked` alert and clears the dict entry. Subsequent SELL emits for that position behave as fresh emits (no suppression, no repeat alert). Repeat alerts within the same session for the same position are NOT this sprint's problem.

10. **Path #1 mechanism (H2 amend / H4 hybrid / H1 cancel-and-await) handling the specific case where the bracket stop has ALREADY filled at the broker before the trail-stop fires.** Existing DEC-386 S1b path handles this via `_handle_oca_already_filled` short-circuit (`oca group is already filled` exception fingerprint). Sprint 31.92 does NOT modify this path — preserve verbatim. The new mechanism only applies when the bracket stop is in `Submitted`/`PreSubmitted` state.

11. **Synthetic SimulatedBroker scenario representing a partial-fill pattern that doesn't occur in IBKR production.** S5a/S5b fixtures must reflect realistic IBKR partial-fill patterns: granularities matching paper IBKR observed behavior (typically full-quantity fills for market orders, broker-determined partials for large limit orders). Do NOT contrive adversarial partial-fill patterns to stress the ceiling — that's a different sprint's defense-in-depth.

12. **Cleanup of the 6,900 cancel-related ERROR-level lines from the Apr 28 debrief's "Cancel-Race Noise" finding (DEF MEDIUM).** Out of scope — the debrief itself classifies this as LOW-priority log-volume hygiene. NOT a safety defect. Cleanup target: opportunistic future touch.

13. **The 5,348 "minimum of N orders working" IBKR rejections from the Apr 28 debrief.** Per the debrief: "Need circuit breaker at OrderManager level: if a symbol has > N pending SELLs in last M seconds, suppress new SELLs until reconcile completes." That circuit breaker IS effectively delivered by AC2 + AC3 in this sprint (AC2 suppresses SELLs on locate-rejection symbols at position-keyed granularity; AC3 ceiling refuses SELLs that exceed the long quantity per position). A separate per-symbol pending-SELL count circuit breaker is NOT in scope — too speculative without measurement that AC2+AC3 alone are insufficient.

14. **Promotion of DEF-204 to RESOLVED status in CLAUDE.md based on test-suite green AND validation-artifact green ALONE.** AC5 produces falsifiable IN-PROCESS validation artifacts; sprint-close marks DEF-204 as RESOLVED-PENDING-PAPER-VALIDATION. Cessation criterion #5 (5 paper sessions clean post-seal) is what fully closes DEF-204 in operational terms. The doc-sync at sprint-close must NOT use language that implies closure-on-merge. **AC5.1/AC5.2 framing is explicitly in-process logic correctness against SimulatedBroker; the JSONs are NOT production safety evidence.**

15. **Ceiling check at bracket placement (`place_bracket_order`).** **NEW per Round-1 finding H-1.** Bracket children (T1+T2+bracket-stop) are placed atomically against a long position; total bracket-child quantity equals `shares_total` by construction (AC3.2 enumerates ceiling check sites as 5 standalone-SELL sites only, EXCLUDING `place_bracket_order`); OCA enforces atomic cancellation per DEC-117 + DEC-386 S1a. Adding ceiling check at bracket placement would block all bracket placements — cumulative pending+sold (0+0) + requested (sum of T1+T2+stop = `shares_total`) ≤ `shares_total` is technically true at bracket placement, but the architectural intent is that bracket-children placement is governed by DEC-117 atomicity, not by the per-emit ceiling. The ceiling exists to catch RACES across MULTIPLE standalone SELL emit sites, not to gate bracket-children placement. T1/T2/bracket-stop FILLS still increment `cumulative_sold_shares` per AC3.1 (because they ARE real sells; the position IS getting smaller).

16. **Restart-during-active-position scenarios that span multiple sequential entries on the same symbol.** AC3.7's `is_reconstructed = True` posture refuses ALL ARGUS-emitted SELLs on reconstructed positions. The original Round-1 reviewer's proposed `data/argus.db` reconstruction option (a) was explicitly REJECTED in §"Out of Scope" #20 because attribution of historical SELLs to specific positions is ambiguous when multiple sequential entries on the same symbol exist within a session. The conservative refusal posture handles all multi-position-on-symbol restart cases uniformly: ALL such positions are reconstructed AND ALL refuse ARGUS SELLs until Sprint 31.94 D3's policy decision. Operator-manual flatten via `scripts/ibkr_close_all_positions.py` is the only closing mechanism. **Edge case to reject:** asking the implementation to attempt finer-grained per-position restart-recovery that reads historical state. NOT this sprint's work.

17. **Aggregate percentage closure claims in DEC-390.** Per process-evolution lesson F.5 (captured at sprint-close per `doc-update-checklist.md` C10): DEC entries claiming closure should use "structural closure of mechanism X with falsifiable test fixture Y" rather than "closes ~Z% of blast radius." DEC-386's `~98%` claim was empirically falsified 24 hours later; DEC-390 must NOT repeat the pattern. AC6.3 mandates structural framing. **Edge case to reject:** any draft DEC-390 text using "comprehensive," "complete," "fully closed," or "covers ~N%" language. Reviewer halts on these tokens.

---

## Scope Boundaries

### Do NOT modify

- `argus/execution/broker.py` (ABC) — touching the broker ABC is Sprint 31.93's prerogative. AC1's H1 fallback uses the existing DEC-386 S0 signature; H2 amend uses the existing `IBKRBroker.modify_order` interface; no ABC extension needed.
- `argus/execution/alpaca_broker.py` — Sprint 31.95 retirement. Stub remains as-is.
- `argus/execution/simulated_broker.py` (semantic changes) — fixture subclasses in tests are acceptable; semantic modifications are OUT.
- `argus/execution/ibkr_broker.py::place_bracket_order` (DEC-386 S1a OCA threading) — preserve byte-for-byte.
- `argus/execution/ibkr_broker.py::_is_oca_already_filled_error` and `_OCA_ALREADY_FILLED_FINGERPRINT` — re-used by Path #1's existing short-circuit; NOT modified, NOT relocated.
- `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b SAFE-marker path) — preserve verbatim.
- `argus/execution/order_manager.py::reconstruct_from_broker` body BEYOND the single-line addition `position.is_reconstructed = True` per AC3.7 — Sprint 31.94 D1's surface otherwise. Implementer may set `is_reconstructed = True` inside the function but may not modify any other line within the function body.
- `argus/execution/order_manager.py::reconcile_positions` Pass 1 startup branch + Pass 2 EOD branch (DEC-385 L3 + L5) — preserve verbatim.
- `argus/execution/order_manager.py::_check_flatten_pending_timeouts` 3-branch side-check at lines ~3424–3489 (DEF-158 fix anchor `a11c001`) — preserve verbatim. Path #2's NEW upstream detection at `place_order` exception is added in `_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts`, `_escalation_update_stop` exception handlers; the EXISTING 3-branch side-check stays intact.
- `argus/main.py::check_startup_position_invariant` — Sprint 31.94 D2's surface.
- `argus/main.py::_startup_flatten_disabled` flag — Sprint 31.94 D2's surface.
- `argus/main.py:1081` (`reconstruct_from_broker()` call site) — Sprint 31.94 D1's surface.
- `argus/core/health.py::HealthMonitor` consumer + `POLICY_TABLE` 13 existing entries (DEC-388 L2) — preserve. Add ONE new `POLICY_TABLE` entry per AC3.9 (the 14th).
- `argus/core/health.py::rehydrate_alerts_from_db` (DEC-388 L3) — preserve.
- `argus/api/v1/alerts.py` REST endpoints (DEC-388 L4) — preserve.
- `argus/ws/v1/alerts.py` WebSocket endpoint (DEC-388 L4) — preserve.
- `argus/frontend/...` (entire frontend) — zero UI changes; Vitest suite stays at 913.
- `data/operations.db` schema (DEC-388 L3 5-table layout + migration framework) — preserve. New `sell_ceiling_violation` alerts use existing `alert_state` table; no schema migration.
- `data/argus.db` trades/positions/quality_history schemas — preserve. NEW: `is_reconstructed`, `cumulative_pending_sell_shares`, `cumulative_sold_shares` are in-memory `ManagedPosition` fields ONLY, NOT persisted to SQLite.
- DEC-385 / DEC-386 / DEC-388 entries in `docs/decision-log.md` — preserve (per Phase A leave-as-historical decision). DEC-390 is a new entry with cross-references; predecessors are NOT amended in-place.

### Do NOT optimize

- `argus/execution/order_manager.py` hot-path performance beyond the explicit benchmarks in Sprint Spec §"Performance Benchmarks". Correctness > speculative optimization. The file is 4,421 lines and structurally accommodates additional checks at scale.
- Test suite runtime. Adding ~75–95 new tests will cost ~20–35s of suite time; that's expected. Do NOT collapse parametrized tests into table-driven loops to save runtime; per-case granularity is load-bearing for triage when a regression fires.
- IBKR network round-trip patterns. Path #1 H1 cancel-and-await adds ~50–200ms per trail-stop event (fallback only); H2 amend adds ~50ms (preferred). Do NOT batch or pipeline cancellation/amend calls — preserves DEC-117 atomic-bracket invariants.
- Locate-suppression dict GC frequency. Existing OrderManager EOD teardown clears the dict; suppression-timeout fallback (AC2.5) clears entries on broker-verification; do NOT add a separate periodic GC sweep in this sprint.
- Pending-reservation increment/decrement performance. AC3.1's state transitions are simple integer arithmetic; do NOT add atomic operations or locks beyond the implicit asyncio single-threaded ordering — the synchronous-before-await placement is the architectural correctness contract.

### Do NOT refactor

- `argus/execution/order_manager.py` module structure (4,421 lines, multiple class methods, mixed concerns). Tempting to break into smaller files; that's Sprint 31.93 component-ownership work. Preserve current structure verbatim.
- `argus/core/config.py::OrderManagerConfig` Pydantic model class structure beyond ADDING the 3 new fields. Field ordering, validator decorators, docstring style — leave as-is.
- `argus/core/config.py::IBKRConfig::bracket_oca_type` — already exists; AC4 only changes the CONSUMER side (OrderManager). The Pydantic field declaration is preserved (per §"Out of Scope" #22, validator restriction to literal `1` is REJECTED — DEC-386 rollback escape hatch preserved).
- `tests/execution/order_manager/` directory layout. New test files follow existing naming convention (`test_def204_round2_path{1,2}.py`, `test_def204_round2_ceiling.py`, `test_def212_oca_type_wiring.py`); do NOT consolidate into mega-modules.
- DEF-158 retry 3-branch side-check (lines ~3424–3489). Tempting to add a 4th branch for locate-rejection; explicitly REJECTED at Phase A. The locate-rejection detection is upstream (at `place_order` exception in the 4 SELL emit sites), not in the side-check.
- `ManagedPosition` class structure beyond ADDING the 3 new fields (`is_reconstructed`, `cumulative_pending_sell_shares`, `cumulative_sold_shares`). Field ordering, dataclass decorators, default-value patterns — leave as-is.

### Do NOT add

- New alert types beyond `sell_ceiling_violation`. The Apr 28 debrief and the protocol allow it implicitly, but Sprint 31.91 already added `phantom_short`, `phantom_short_retry_blocked`, `eod_residual_shorts`, `eod_flatten_failed`, `cancel_propagation_timeout`, `ibkr_disconnect`, `ibkr_auth_failure`, plus heartbeat — the alert taxonomy is healthy.
- New REST endpoints for ceiling-violation history queries. Existing `/api/v1/alerts/history` filtered by `alert_type=sell_ceiling_violation` covers it.
- New Pydantic config models. The 3 new fields land on EXISTING `OrderManagerConfig`. The 1 existing `IBKRConfig.bracket_oca_type` field gains a new consumer (OrderManager) but no schema change.
- New SQLite tables. `sell_ceiling_violation` alerts persist via DEC-388 L3 `alert_state` table.
- New CLI tools beyond the 4 spike/validation scripts (`spike_def204_round2_path1.py`, `spike_def204_round2_path2.py`, `validate_def204_round2_path1.py`, `validate_def204_round2_path2.py`). The composite validation lives in `tests/integration/test_def204_round2_validation.py` and produces its JSON artifact as a test side-effect per AC5.3.
- New helper modules under `argus/execution/`. The 2 new helpers (`_is_locate_rejection` in `ibkr_broker.py`, `_check_sell_ceiling` in `order_manager.py`) live in their respective existing modules.
- A `sell_ceiling_violations` table separate from `alert_state`. Re-use existing infrastructure.
- A `/api/v1/orders/sell_volume_ceiling_status` endpoint for monitoring. Out of scope. The alert path is the operator interface.
- A separate `_handle_locate_suppression_timeout` helper in a new module. The broker-verification logic per AC2.5 lives inline in `_check_flatten_pending_timeouts` housekeeping loop OR as a private method on OrderManager.

---

## Interaction Boundaries

### This sprint does NOT change the behavior of:

- `Broker.cancel_all_orders()` ABC contract. DEC-386 S0's signature `cancel_all_orders(symbol: str | None = None, *, await_propagation: bool = False)` is consumed unchanged in H1 fallback path. AC1 calls it with `(symbol=position.symbol, await_propagation=True)` — same call shape DEC-386 S1c uses.
- `IBKRBroker.place_bracket_order()` external contract. Bracket OCA threading semantics, atomic placement, error 201 handling — all preserved.
- `IBKRBroker.place_order()` external contract. The `place_order(Order)` API is unchanged. Path #2's NEW behavior is at the CALLER side: callers wrap `place_order(SELL)` calls with `_check_sell_ceiling` pre-check + `_is_locate_suppressed` pre-check + `_is_locate_rejection` post-classification, but the broker method itself is unchanged.
- `IBKRBroker.modify_order()` external contract. Existing interface; AC1's H2 path calls it with `(stop_order_id, new_aux_price=current_price)`. NO new keyword arguments, NO new return-value semantics.
- `OrderManager.on_fill()` event handler external contract. Internal: AC3.1 enumerates `cumulative_pending_sell_shares` decrement + `cumulative_sold_shares` increment for SELL fills. Existing T1/T2/bracket-stop fill processing preserved.
- `Position` / `ManagedPosition` data model external contract. AC3.1 + AC3.7 add THREE new fields (`cumulative_pending_sell_shares: int = 0`, `cumulative_sold_shares: int = 0`, `is_reconstructed: bool = False`) with default values; existing serialization and DB columns preserved. New fields are in-memory only — NOT persisted to SQLite (per Sprint 35+ DEF-209 backlog deferral; conservative `is_reconstructed` posture handles restart-safety per AC3.7).
- `SystemAlertEvent` schema. DEC-385 L2 added `metadata: dict[str, Any] | None`; preserved. New `sell_ceiling_violation` alert uses existing schema.
- `OrderManagerConfig` external contract. Adding 3 new fields with defaults is backward-compatible; existing YAML configs without these fields default safely.
- `IBKRConfig` external contract. AC4.1 only changes the CONSUMER side; the field definition is unchanged. Per §"Out of Scope" #22, validator restriction to literal `1` is REJECTED.
- `HealthMonitor.consume_alert()` consumer logic. AC3.9 adds ONE `POLICY_TABLE` entry; the consumer logic is preserved.
- WebSocket `/ws/v1/alerts` event payload schema (4 lifecycle deltas). New `sell_ceiling_violation` alert flows through `alert_active` delta unchanged.
- REST `/api/v1/alerts/active`, `/history`, `/{id}/acknowledge`, `/{id}/audit`. Behavior unchanged.

### This sprint does NOT affect:

- Any frontend component. Zero `.tsx`, `.ts`, `.css`, or test file in `frontend/` is touched.
- Any catalyst pipeline component (CatalystPipeline, CatalystClassifier, BriefingGenerator, CatalystStorage). Zero changes.
- Any quality engine component (SetupQualityEngine, DynamicPositionSizer, QualitySignalEvent flow). Zero changes.
- Any data service component (DatabentoDataService, IntradayCandleStore, FMP/Finnhub clients, UniverseManager). Zero changes.
- Any backtesting component (BacktestEngine, VectorBT path, replay harness, PatternBacktester). Zero changes.
- Any AI Layer component (ClaudeClient, PromptManager, ActionManager, ConversationManager). Zero changes.
- Strategy modules (any file in `argus/strategies/`). Zero changes — entry-side logic is unaffected by exit-side mechanism changes.
- Pattern modules (any file in `argus/strategies/patterns/`). Zero changes.
- Risk Manager (`argus/core/risk_manager.py`). Zero changes — DEC-027 approve-with-modification posture preserved.
- Orchestrator (`argus/core/orchestrator.py`). Zero changes.
- `data/argus.db` trades/positions/quality_history schemas. Zero migrations.
- `data/counterfactual.db`, `data/experiments.db`, `data/learning.db`, `data/catalyst.db`, `data/vix_landscape.db`, `data/regime_history.db`, `data/evaluation.db`. Zero schema changes.

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
| `ManagedPosition.cumulative_pending_sell_shares` + `cumulative_sold_shares` SQLite persistence | Sprint 35+ Learning Loop V2 (DEF-209 extended scope) | DEF-209 |
| Standalone `sell_volume_ceiling_status` REST endpoint | Unscheduled (out of scope here) | (no DEF) |
| Locate-suppression dict reconnect-event awareness (couples with `IBKRReconnectedEvent` consumer) | Sprint 31.94 | (NEW: filed at S3a as deferred sub-item, no DEF; mitigated by AC2.5 broker-verification) |
| Locate-rejection error-string drift quarterly re-validation | Operational hygiene, post-Sprint-31.92-merge | RSK-DEC-390-FINGERPRINT (proposed at sprint-close) |
| Path #1 H2 amend-stop-price IBKR-API-version assumption documentation | `docs/live-operations.md` paragraph at sprint-close | RSK-DEC-390-AMEND (proposed at sprint-close) |
| Path #1 H1 cancel-and-await unprotected-window documentation | `docs/live-operations.md` paragraph at sprint-close (only if H1 selected) | RSK-DEC-390-CANCEL-AWAIT-LATENCY (proposed at sprint-close, conditional on H1 selection) |

---

## Adversarial Round 2 Reference

The Adversarial Review Input Package Round 2 (Phase C, artifact #8 revised) embeds this Spec by Contradiction verbatim. Round 2 reviewers should specifically scrutinize:

1. Whether the C-1 fix (pending reservation pattern) introduces NEW races at state-transition boundaries — e.g., partial-fill arriving concurrently with a cancel-rejection on the same `ManagedPosition`.
2. Whether the C-2 fix (`is_reconstructed` refusal posture) creates legitimate-flatten-blocked failure modes that the operator daily-flatten script doesn't catch — specifically, EOD scenarios on reconstructed positions.
3. Whether the H-3 fix (broker-verification at suppression timeout) introduces NEW failure modes — e.g., what if `broker.get_positions()` itself fails or returns stale data during the verification window?
4. Whether the H-4 fix (startup CRITICAL warning) is operationally meaningful — could the warning be missed in log noise?
5. Whether the M-1 fix (S1b spike measuring hard-to-borrow microcaps) actually finds released-held-orders in the spike trials — what if no symbols in the operator-curated list actually get held during paper hours?
6. Whether the M-3 fix (Pytest with JSON side-effect) genuinely preserves freshness — what if the daily CI workflow is misconfigured or fails silently?
7. Whether items 20–23 in §"Out of Scope" (specifically rejecting reviewer-proposed alternatives) are correctly justified or whether one of them should be reopened.
8. Whether new Edge Case to Reject #1 (race scenario via reservation pattern) is structurally airtight.
9. Whether new Edge Case to Reject #15 (ceiling check at bracket placement excluded) is correctly bounded — i.e., what about non-standard bracket-children placements that might exist in DEC-386 broker-only paths?
10. Whether new Edge Case to Reject #16 (multi-position-on-symbol restart scenarios) creates an operationally undesirable "trapped capital" failure mode — and whether Sprint 31.94 D3's policy decision adequately resolves it.
11. Whether new Edge Case to Reject #17 (no aggregate percentage claims) is structurally enforceable or whether it relies on implementer discipline alone.
12. Whether the deferred items table (especially the locate-suppression dict reconnect-event coupling) accumulates too much technical debt at the Sprint 31.94 boundary.