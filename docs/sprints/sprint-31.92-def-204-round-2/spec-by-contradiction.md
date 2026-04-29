# Sprint 31.92: What This Sprint Does NOT Do

This document defines the boundaries of Sprint 31.92 — DEF-204 Round 2. It exists to prevent scope creep during implementation and to give the adversarial reviewer (Phase C-1) and Tier 2 reviewer (per-session) clear boundaries to check. Sprint 31.91 Tier 3 #1 explicitly flagged scope creep as a concern; this document is the structural defense against that pattern recurring.

The sprint focuses narrowly on closing the two empirically-falsifying paths from the 2026-04-28 paper-session debrief, plus a structural ceiling as defense-in-depth, plus the DEF-212 rider. Everything else — even items thematically adjacent to safety, reconciliation, or order-management hygiene — is explicitly out of scope.

---

## Out of Scope

These items are related to the sprint goal but are explicitly excluded:

1. **Structural refactor of `_flatten_position`, `_trail_flatten`, `_escalation_update_stop`, or `_check_flatten_pending_timeouts` beyond the explicit safety properties enumerated in AC1–AC4.** These four functions are touched by 6 of the 10 sessions (S2a/S2b/S3a/S3b/S4a + S4b indirectly via construction surface) — that's a maximum-overlap zone. The temptation to "while I'm in there, also fix X" must be resisted. Structural cleanup is Sprint 31.93 component-ownership scope.

2. **Modifications to DEC-386's 4-layer OCA architecture (Sessions 0/1a/1b/1c).** Specifically: `Broker.cancel_all_orders(symbol, *, await_propagation)` ABC contract, `IBKRBroker.place_bracket_order` OCA threading, `ManagedPosition.oca_group_id`, `_handle_oca_already_filled`, `# OCA-EXEMPT:` exemption mechanism, `reconstruct_from_broker()` STARTUP-ONLY docstring. All preserved byte-for-byte (regression invariant R6). Sprint 31.92 ADDS to this architecture (cancel-and-await before SELL on Path #1; cumulative_sold ceiling on AC4); it does NOT modify the existing layers.

3. **Modifications to DEC-385's 6-layer side-aware reconciliation contract.** Specifically: `reconcile_positions()` Pass 1 startup branch + Pass 2 EOD branch, `phantom_short_gated_symbols` audit table, DEF-158 retry 3-branch side-check, `phantom_short_retry_blocked` alert path. Path #2's suppression-timeout fallback REUSES the existing `phantom_short_retry_blocked` alert type — it does NOT introduce new behavior in DEC-385's surfaces.

4. **Relocation of `_is_oca_already_filled_error` from `argus/execution/ibkr_broker.py` to `argus/execution/broker.py`.** Tier 3 #1 Concern A (Sprint 31.91, 2026-04-27) called for this relocation. Phase A explicitly DEFERRED it to Sprint 31.93 component-ownership because (a) `broker.py` ABC modification is the natural home, (b) Sprint 31.92 already has 6 sessions touching `order_manager.py` and adding `broker.py` to the modify list expands blast radius unnecessarily, (c) the helper's current location is functionally correct — the relocation is cosmetic.

5. **DEF-211 D1+D2+D3 (Sprint 31.94 sprint-gating items).** Specifically: `ReconstructContext` enum + parameter threading on `reconstruct_from_broker()`, IMPROMPTU-04 startup invariant gate refactor, boot-time adoption-vs-flatten policy decision for broker-only LONG positions. RSK-DEC-386-DOCSTRING bound stays bound by Sprint 31.94. Sprint 31.92 must NOT touch `argus/main.py:1081` (the `reconstruct_from_broker()` call site) or `check_startup_position_invariant()`.

6. **DEF-194/195/196 reconnect-recovery work (Sprint 31.94).** Specifically: IBKR `ib_async` stale position cache after reconnect, `max_concurrent_positions` divergence after disconnect-recovery, DEC-372 stop-retry-exhaustion cascade events. The 38 "Stop retry failed → Emergency flattening" events on Apr 28 are a Path #1 surface (covered by AC1.3's `_resubmit_stop_with_retry` emergency-flatten branch); the cluster-wide reconnect-recovery analysis is NOT in scope.

7. **`evaluation.db` 22GB bloat or VACUUM-on-startup behavior.** Sprint 31.915 already merged DEC-389 retention + VACUUM. The Apr 28 debrief's secondary finding (eval.db forced premature shutdown) is closed.

8. **`ibkr_close_all_positions.py` post-run verification feature.** The Apr 28 debrief flagged this as a HIGH-severity DEF-231 candidate. Phase A retracted it: operator confirmed 2026-04-29 that the 43 pre-existing shorts at boot were missed-run human error, NOT a script defect. The script does its job when run; building a verification harness around operator hygiene would not have caught the human-error case (operator could equally forget to run the verification command). If automation is desired, that's a future operator-tooling enhancement, opportunistic and post-revenue. NOT this sprint.

9. **The 4,700 broker-overflow routings noted in the Apr 28 debrief.** Debrief explicitly defers: "Possibly fine; possibly indicates `max_concurrent_positions` is too tight for the actual signal volume." Requires a separate analysis pass against `max_concurrent_positions: 50` sizing. NOT a safety defect; out of scope.

10. **DEF-215 reconciliation-WARNING throttling.** Already DEFERRED with sharp revisit trigger ("≥10 consecutive cycles AFTER Sprint 31.91 has been sealed for ≥5 paper sessions"). Sprint 31.92 closure does not satisfy the trigger; DEF-215 stays deferred.

11. **Sprint 31B Research Console / Variant Factory work.** Conceptually adjacent (both touch the post-31.91 horizon) but functionally orthogonal. Sprint 31B is Stage 1 strategy-screening infrastructure; Sprint 31.92 is execution-layer safety. Sequenced after 31.92 per Phase 0 routing.

12. **Sprint 31.95 Alpaca retirement (DEF-178/183).** Wholly orthogonal scope.

13. **New alert observability features beyond a single `POLICY_TABLE` entry for `sell_ceiling_violation`.** Specifically out: `AlertBanner` UX changes, `AlertToastStack` queue capacity adjustments, new REST endpoints, new WebSocket event types, additional per-alert audit-trail enrichment. AC3.7 ADDS a single `POLICY_TABLE` entry (`operator_ack_required=True`, `auto_resolution_predicate=None`) and updates the AST exhaustiveness regression guard — that's the entire alert-system delta.

14. **Performance optimization beyond the explicit benchmarks in the Sprint Spec.** AC's measure ≤200ms cancel-and-await, ≤10µs ceiling check, ≤5µs locate-suppression check, ≤30s suite runtime regression. If any actual measurement exceeds these targets, halt and surface — do NOT optimize speculatively.

15. **Backporting AC1/AC2/AC4 fixes to Sprint 31.91-tagged code.** Sprint 31.92 lands at HEAD post-31.91-seal. There is no scenario where 31.92's mechanism would be backported separately.

16. **Live trading enablement.** Sprint 31.91's cessation criterion #5 (5 paper sessions clean post-seal) reset on Apr 28. Sprint 31.92's seal STARTS a new 5-session counter. Live trading remains gated by that counter PLUS Sprint 31.91 Sprint Spec §D7's pre-live paper stress test under live-config simulation (DEF-208 — separately scoped).

17. **Documentation rewrites of `docs/architecture.md` §3.7 Order Manager beyond what AC's require.** AC-required: short subsection or paragraph about (a) cancel-and-await mechanism on `_trail_flatten`, (b) `_is_locate_rejection` + suppression dict, (c) `cumulative_sold_shares` ceiling, (d) `bracket_oca_type` flow from config to `OrderManager.__init__`. Anything beyond these four items is OUT.

18. **Restructuring or extending `SimulatedBroker` semantically.** S5a + S5b validation scripts may add NEW test fixtures (e.g., `SimulatedBrokerWithLocateRejection`) but must not modify SimulatedBroker's existing fill-model semantics, immediate-fill behavior, or OCA simulation. Existing tests pass without modification.

19. **Sprint-close cessation-criterion celebration.** Sprint 31.92 sealing satisfies cessation criterion #4 (sprint sealed) for the new criterion-#5 counter — but criterion #5 itself (5 paper sessions clean post-Sprint-31.92 seal) starts at 0/5 again. Operator daily-flatten mitigation continues.

---

## Edge Cases to Reject

The implementation should NOT handle these cases in this sprint:

1. **Multi-symbol concurrent SELL fills hitting the ceiling at exactly the same instant (sub-millisecond race within `on_fill`).** Expected behavior: existing OrderManager event-handler serialization (asyncio single-threaded event loop) prevents this. If a future architectural change introduces concurrent fill processing, that's a separate problem. AC3 ceiling assumes single-threaded `on_fill` — do NOT add cross-position locking.

2. **IBKR returning a `modifyOrder` rejection during Path #1 OPTION (a) for reasons other than "stop price invalid" (e.g., 201 margin).** Out of scope. If S1a spike selects OPTION (a), the impl assumes amend rejections are rare AND non-deterministic ones are caught by AC1.5's regression test (mock `IBKRBroker.modify_order` to raise; assert fall-through behavior). Production-side robustness for unusual amend rejections is post-revenue concern.

3. **`cumulative_sold_shares` integer overflow.** A `ManagedPosition` that sold > 2³¹ shares is architecturally infeasible (max position size is bounded by Risk Manager checks at single-share scale). Use `int`, not `int64` or `Decimal`. No overflow regression test.

4. **Operator manually placing SELL orders at IBKR outside ARGUS during a session.** Sprint 30 short-selling territory; reconciliation surface (DEC-385) catches the resulting state mismatch. AC4 ceiling applies to ARGUS-emitted SELLs only — manual operator actions are not in `_check_sell_ceiling`'s purview.

5. **Mid-session reconnect race with locate-suppression dict.** If IBKR Gateway disconnects and reconnects mid-session, existing held orders are invalidated (DEF-194/195/196 cluster, Sprint 31.94). The locate-suppression dict in Sprint 31.92 does NOT account for reconnect events — Sprint 31.94 will couple `IBKRReconnectedEvent` consumer logic to dict-clear. Until then: if a reconnect happens during a suppression window, the dict entry stays; either (a) suppression-timeout fallback fires correctly when window expires, OR (b) operator restarts; both are acceptable for paper trading.

6. **Locate-rejection error string variants ("not available for short" without the "contract is" prefix; "no inventory available"; non-English locales).** S1b spike captures the exact current string `"contract is not available for short sale"`; AC2.1's substring fingerprint matches that exact substring (case-insensitive). Variants are caught by H5's "rules-out-if" condition at S1b. If S1b finds a variant, regex pattern is broadened at S3a. If S1b is conclusive (single string), do NOT speculatively broaden — fingerprint regression test fails noisy if string drifts.

7. **`_check_sell_ceiling` violation IN PRODUCTION-LIVE-MODE configurable to "warn-only" rather than "refuse SELL".** AC3.6 defaults `long_only_sell_ceiling_enabled = true` — fail-closed. The flag exists for explicit operator override during emergency rollback ONLY. There is NO third state ("warn-only"). Booleans only.

8. **Per-`ManagedPosition` SELL ceiling with cross-position aggregation across same symbol.** AC3.4 explicitly: per-`ManagedPosition`, NOT per-symbol. If two ManagedPositions on AAPL exist (sequential entries within the morning window), each has its own ceiling. Cross-position aggregation is the existing Risk Manager max-single-stock-exposure check at the entry layer (DEC-027), which is OUT of scope to modify here.

9. **Suppression-window expiration emits more than one alert per symbol per session.** AC2.5: when suppression expires, the next SELL emit at that symbol publishes ONE `phantom_short_retry_blocked` alert and clears the dict entry. Subsequent SELL emits for that symbol behave as fresh emits (no suppression, no repeat alert). Repeat alerts within the same session for the same symbol are NOT this sprint's problem.

10. **Path #1 mechanism (cancel-and-await OR amend-stop-price) handling the specific case where the bracket stop has ALREADY filled at the broker before the trail-stop fires.** Existing DEC-386 S1b path handles this via `_handle_oca_already_filled` short-circuit (`oca group is already filled` exception fingerprint). Sprint 31.92 does NOT modify this path — preserve verbatim. The new mechanism only applies when the bracket stop is in `Submitted`/`PreSubmitted` state.

11. **Synthetic SimulatedBroker scenario representing a partial-fill pattern that doesn't occur in IBKR production.** S5a/S5b fixtures must reflect realistic IBKR partial-fill patterns: granularities matching paper IBKR observed behavior (typically full-quantity fills for market orders, broker-determined partials for large limit orders). Do NOT contrive adversarial partial-fill patterns to stress the ceiling — that's a different sprint's defense-in-depth.

12. **Cleanup of the 6,900 cancel-related ERROR-level lines from the Apr 28 debrief's "Cancel-Race Noise" finding (DEF MEDIUM).** Out of scope — the debrief itself classifies this as LOW-priority log-volume hygiene. NOT a safety defect. Cleanup target: opportunistic future touch.

13. **The 5,348 "minimum of N orders working" IBKR rejections from the Apr 28 debrief.** Per the debrief: "Need circuit breaker at OrderManager level: if a symbol has > N pending SELLs in last M seconds, suppress new SELLs until reconcile completes." That circuit breaker IS effectively delivered by AC2 + AC4 in this sprint (AC2 suppresses SELLs on locate-rejection symbols; AC4 ceiling refuses SELLs that exceed the long quantity). A separate per-symbol pending-SELL count circuit breaker is NOT in scope — too speculative without measurement that AC2+AC4 alone are insufficient.

14. **Promotion of DEF-204 to RESOLVED status in CLAUDE.md based on test-suite green AND validation-artifact green ALONE.** AC5 produces falsifiable validation artifacts; sprint-close marks DEF-204 as RESOLVED-PENDING-PAPER-VALIDATION. Cessation criterion #5 (5 paper sessions clean post-seal) is what fully closes DEF-204 in operational terms. The doc-sync at sprint-close must NOT use language that implies closure-on-merge.

---

## Scope Boundaries

### Do NOT modify

- `argus/execution/broker.py` (ABC) — touching the broker ABC is Sprint 31.93's prerogative. AC1's cancel-and-await uses the existing DEC-386 S0 signature; no ABC extension needed.
- `argus/execution/alpaca_broker.py` — Sprint 31.95 retirement. Stub remains as-is.
- `argus/execution/simulated_broker.py` — semantic extensions OUT. Test fixtures may add subclasses or wrappers; the production class stays unchanged.
- `argus/execution/ibkr_broker.py::place_bracket_order` (DEC-386 S1a OCA threading) — preserve byte-for-byte.
- `argus/execution/ibkr_broker.py::_is_oca_already_filled_error` and `_OCA_ALREADY_FILLED_FINGERPRINT` — re-used by Path #1's existing short-circuit; NOT modified, NOT relocated.
- `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b SAFE-marker path) — preserve verbatim.
- `argus/execution/order_manager.py::reconstruct_from_broker` — Sprint 31.94 D1's surface. NOT modified.
- `argus/execution/order_manager.py::reconcile_positions` Pass 1 startup branch + Pass 2 EOD branch (DEC-385 L3 + L5) — preserve verbatim.
- `argus/execution/order_manager.py::_check_flatten_pending_timeouts` 3-branch side-check at lines ~3424–3489 (DEF-158 fix anchor `a11c001`) — preserve verbatim. Path #2's NEW upstream detection at `place_order` exception is added in `_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts`, `_escalation_update_stop` exception handlers; the EXISTING 3-branch side-check stays intact.
- `argus/main.py::check_startup_position_invariant` — Sprint 31.94 D2's surface.
- `argus/main.py::_startup_flatten_disabled` flag — Sprint 31.94 D2's surface.
- `argus/core/health.py::HealthMonitor` consumer + `POLICY_TABLE` 13 existing entries (DEC-388 L2) — preserve. Add ONE new `POLICY_TABLE` entry per AC3.7 (the 14th).
- `argus/core/health.py::rehydrate_alerts_from_db` (DEC-388 L3) — preserve.
- `argus/api/v1/alerts.py` REST endpoints (DEC-388 L4) — preserve.
- `argus/ws/v1/alerts.py` WebSocket endpoint (DEC-388 L4) — preserve.
- `argus/frontend/...` (entire frontend) — zero UI changes; Vitest suite stays at 913.
- `data/operations.db` schema (DEC-388 L3 5-table layout + migration framework) — preserve. New `sell_ceiling_violation` alerts use existing `alert_state` table; no schema migration.
- DEC-385 / DEC-386 / DEC-388 entries in `docs/decision-log.md` — preserve (per Phase A leave-as-historical decision). DEC-390 is a new entry with cross-references; predecessors are NOT amended in-place.

### Do NOT optimize

- `argus/execution/order_manager.py` hot-path performance beyond the explicit benchmarks in Sprint Spec §"Performance Benchmarks". Correctness > speculative optimization. The file is 4,421 lines and structurally accommodates additional checks at scale.
- Test suite runtime. Adding ~60–85 new tests will cost ~10–20s of suite time; that's expected. Do NOT collapse parametrized tests into table-driven loops to save runtime; per-case granularity is load-bearing for triage when a regression fires.
- IBKR network round-trip patterns. Path #1 cancel-and-await adds ~50–200ms per trail-stop event; that's acceptable per AC's. Do NOT batch or pipeline cancellation calls — preserves DEC-117 atomic-bracket invariants.
- Locate-suppression dict GC frequency. Existing OrderManager EOD teardown clears the dict; do NOT add a separate periodic GC sweep in this sprint.

### Do NOT refactor

- `argus/execution/order_manager.py` module structure (4,421 lines, multiple class methods, mixed concerns). Tempting to break into smaller files; that's Sprint 31.93 component-ownership work. Preserve current structure verbatim.
- `argus/core/config.py::OrderManagerConfig` Pydantic model class structure beyond ADDING the 3 new fields. Field ordering, validator decorators, docstring style — leave as-is.
- `argus/core/config.py::IBKRConfig::bracket_oca_type` — already exists; AC4 only changes the CONSUMER side (OrderManager). The Pydantic field declaration is preserved.
- `tests/execution/order_manager/` directory layout. New test files follow existing naming convention (`test_def204_round2_path{1,2}.py`, `test_def204_round2_ceiling.py`, `test_def212_oca_type_wiring.py`); do NOT consolidate into mega-modules.
- DEF-158 retry 3-branch side-check (lines ~3424–3489). Tempting to add a 4th branch for locate-rejection; explicitly REJECTED at Phase A. The locate-rejection detection is upstream (at `place_order` exception in the 4 SELL emit sites), not in the side-check.

### Do NOT add

- New alert types beyond `sell_ceiling_violation`. The Apr 28 debrief and the protocol allow it implicitly, but Sprint 31.91 already added `phantom_short`, `phantom_short_retry_blocked`, `eod_residual_shorts`, `eod_flatten_failed`, `cancel_propagation_timeout`, `ibkr_disconnect`, `ibkr_auth_failure`, plus heartbeat — the alert taxonomy is healthy.
- New REST endpoints for ceiling-violation history queries. Existing `/api/v1/alerts/history` filtered by `alert_type=sell_ceiling_violation` covers it.
- New Pydantic config models. The 3 new fields land on EXISTING `OrderManagerConfig`. The 1 existing `IBKRConfig.bracket_oca_type` field gains a new consumer (OrderManager) but no schema change.
- New SQLite tables. `sell_ceiling_violation` alerts persist via DEC-388 L3 `alert_state` table.
- New CLI tools beyond the 5 spike/validation scripts (`spike_def204_round2_path1.py`, `spike_def204_round2_path2.py`, `validate_def204_round2_path1.py`, `validate_def204_round2_path2.py`, `validate_def204_round2_composite.py`).
- New helper modules under `argus/execution/`. The 2 new helpers (`_is_locate_rejection` in `ibkr_broker.py`, `_check_sell_ceiling` in `order_manager.py`) live in their respective existing modules.
- A `sell_ceiling_violations` table separate from `alert_state`. Re-use existing infrastructure.
- A `/api/v1/orders/sell_volume_ceiling_status` endpoint for monitoring. Out of scope. The alert path is the operator interface.

---

## Interaction Boundaries

### This sprint does NOT change the behavior of:

- `Broker.cancel_all_orders()` ABC contract. DEC-386 S0's signature `cancel_all_orders(symbol: str | None = None, *, await_propagation: bool = False)` is consumed unchanged. AC1 calls it with `(symbol=position.symbol, await_propagation=True)` — same call shape DEC-386 S1c uses.
- `IBKRBroker.place_bracket_order()` external contract. Bracket OCA threading semantics, atomic placement, error 201 handling — all preserved.
- `IBKRBroker.place_order()` external contract. The `place_order(Order)` API is unchanged. Path #2's NEW behavior is at the CALLER side: callers wrap `place_order(SELL)` calls with `_check_sell_ceiling` pre-check + `_is_locate_rejection` post-classification, but the broker method itself is unchanged.
- `OrderManager.on_fill()` event handler external contract. Internal: AC3.1 increments `cumulative_sold_shares` for SELL fills. Existing T1/T2/bracket-stop fill processing preserved.
- `Position` / `ManagedPosition` data model external contract. AC3.1 adds ONE new field (`cumulative_sold_shares: int = 0`) with default value; existing serialization and DB columns preserved. New field is in-memory only — NOT persisted to SQLite (per Sprint 35+ Learning Loop V2 backlog for `redundant_exit_observed`-class fields).
- `SystemAlertEvent` schema. DEC-385 L2 added `metadata: dict[str, Any] | None`; preserved. New `sell_ceiling_violation` alert uses existing schema.
- `OrderManagerConfig` external contract. Adding 3 new fields with defaults is backward-compatible; existing YAML configs without these fields default safely.
- `IBKRConfig` external contract. AC4.1 only changes the CONSUMER side; the field definition is unchanged.
- `HealthMonitor.consume_alert()` consumer logic. AC3.7 adds ONE `POLICY_TABLE` entry; the consumer logic is preserved.
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
| Boot-time adoption-vs-flatten policy decision for broker-only LONG positions (D3) | Sprint 31.94 | DEF-211 D3 |
| `IBKRReconnectedEvent` producer wiring (gates DEF-222 audit) | Sprint 31.94 | DEF-194, DEF-195, DEF-196, DEF-222 |
| RejectionStage enum split (`MARGIN_CIRCUIT` + `TrackingReason`) | Sprint 31.94 | DEF-177, DEF-184 |
| DEF-014 IBKR emitter TODOs | Sprint 31.94 | DEF-014 (closed in 31.91 but emitter TODO remnants) |
| Alpaca incubator retirement | Sprint 31.95 | DEF-178, DEF-183 |
| `evaluation.db` 22GB legacy file VACUUM (operator-side, post-Sprint-31.915 retention) | Operator action, immediate | (operational task, not DEF) |
| Reconciliation-WARNING per-cycle throttling | Deferred (revisit if observed ≥10 cycles post-Sprint-31.92-seal-+-5-paper-sessions) | DEF-215 |
| 4,700 broker-overflow routings analysis (`max_concurrent_positions: 50` sizing review) | Unscheduled (separate analysis pass) | (filed at Apr 28 debrief Action Items §4 — no DEF) |
| 6,900 cancel-related ERROR-line log-volume cleanup | Opportunistic / unscheduled | (Apr 28 debrief Findings §LOW) |
| Per-symbol pending-SELL count circuit breaker (separate from AC2 + AC4) | Unscheduled (revisit if AC2+AC4 prove insufficient post-merge) | (Apr 28 debrief Findings §MEDIUM) |
| `ibkr_close_all_positions.py` post-run verification feature | Unscheduled — operator-tooling, not a defect | (no DEF; retracted at Phase A 2026-04-29) |
| Live-trading test fixture (`tests/integration/test_live_config_stress.py`) | Sprint 31.93 OR Sprint 31.94 | DEF-208 |
| `ManagedPosition.redundant_exit_observed` SQLite persistence | Sprint 35+ Learning Loop V2 | DEF-209 (folded by DEC-386 Tier 3 #1) |
| Standalone `sell_volume_ceiling_status` REST endpoint | Unscheduled (out of scope here) | (no DEF) |
| Locate-suppression dict reconnect-event awareness | Sprint 31.94 (couples with `IBKRReconnectedEvent` producer) | (NEW: filed at S3a as deferred sub-item, no DEF) |
| Locate-rejection error-string drift quarterly re-validation | Operational hygiene, post-Sprint-31.92-merge | RSK-DEC-390-FINGERPRINT (proposed at sprint-close) |
| Path #1 OPTION (a) amend-stop-price IBKR-API-version assumption documentation | `docs/live-operations.md` paragraph at sprint-close (if H2 selected by S1a) | RSK-DEC-390-AMEND (proposed at sprint-close, conditional on spike outcome) |

---

## Adversarial Review Reference

The Adversarial Review Input Package (Phase C, artifact #8) will include this Spec by Contradiction verbatim. Adversarial reviewers should specifically scrutinize:

1. Whether items 1–3 in "Out of Scope" can credibly hold during 6+ sessions of `order_manager.py` modification (the file is the maximum-overlap zone).
2. Whether item 4 (`_is_oca_already_filled_error` relocation deferral) creates any concrete risk of code-drift or duplicate-helper bugs in this sprint.
3. Whether the AMD-2 invariant modification (R10 in regression-checklist) is correctly scoped — i.e., does any other code path depend on AMD-2's "sell before cancel" ordering beyond `_trail_flatten`?
4. Whether the locate-suppression dict's reconnect-blindness (Edge Case to Reject #5) is acceptable for paper trading, given that paper IBKR Gateway disconnects ARE observed in production (Apr 22 / Apr 23 debriefs).
5. Whether `cumulative_sold_shares` being in-memory only (not persisted) creates risk if ARGUS restarts mid-session with active positions — i.e., is the field correctly reconstructed via `reconstruct_from_broker()` on startup, OR does this reconstruction have a gap?
6. Whether the "Do NOT add a 4th branch to DEF-158 retry side-check" decision (item #13 in Edge Cases to Reject) is correct — could a 4th branch be cleaner than upstream-at-`place_order` detection?