# Sprint 31.91 — Work Journal Register

> **Purpose:** Durable register of Sprint 31.91 Work Journal state, refreshed after every session close-out and Tier 3 verdict per `protocols/in-flight-triage.md` § "Per-Session Register Discipline" (workflow v1.2.0). Functions as a compaction-resilient backstop for the Work Journal conversation.
>
> **Update discipline:** Refreshed after every session close-out AND every Tier 3 verdict. Even sessions that don't materially change the register receive a refresh with updated test counts, commit SHAs, and timestamps. Git history of this file is the session-grain audit trail.
>
> **Source of truth:** This file is authoritative for register state. The Work Journal conversation IS the editing surface; this file is the persisted truth. If the conversation and this file conflict, this file wins.

---



## Last Refresh

| Field | Value |
|---|---|
| **Refreshed at** | 2026-04-28, post-Impromptu-B CLEAR |
| **Anchor commit** | `8efa72e` (Impromptu B impl); upstream `bb02174` (post-Impromptu-A register refresh) + `e78a994`/`ad1e7ff` (Impromptu A impl + SHA backfill) |
| **Sessions complete** | 0, 1a, 1b, 1c, 2a, 2b.1, 2b.2, 2c.1, 2c.2 (+ DEF-216 hotfix), 2d, 3, 4, 5a.1, 5a.2, 5b, Impromptu A, **Impromptu B** |
| **Tier 3 reviews complete** | #1 (PROCEED), #2 (PROCEED with conditions; AMENDED 2026-04-28) |
| **Active session** | None — between sessions; **Session 5c is next** (BOTH conditions MET: Impromptu A landed CLEAR ✅; Impromptu B landed CLEAR ✅) |
| **Sprint phase** | Backend SEALED + Backend HARDENING COMPLETE (Impromptu A) + Producer Wiring COMPLETE (Impromptu B with DEF-217 dual-layer regression coverage); **frontend integration phase BEGINS at Session 5c** |
| **Workflow protocol version** | 1.3.0 (mid-sprint doc-sync protocol + structural anchors); `tier-3-review.md` independently at 1.0.2 |

---

## Sprint Identity (Pinned)

- **Sprint:** `sprint-31.91-reconciliation-drift`
- **Predecessor:** Sprint 31.9 (sealed 2026-04-24)
- **Mode:** HITL on `main`
- **Primary defects:** DEF-204 (reconciliation drift / phantom-short — all architectural layers LIVE + falsifiable validation gate LIVE), DEF-014 (alert observability gap — **producer side RESOLVED at S5b**; full RESOLUTION at Session 5e)
- **Operational mitigation:** Operator runs `scripts/ibkr_close_all_positions.py` daily — REQUIRED, NOT OPTIONAL. Cessation criteria #1 + #2 + #3 SATISFIED post-S4; #4 + #5 still pending
- **Reserved DECs at planning:** DEC-385 (MATERIALIZED at S2d), DEC-386 (MATERIALIZED at Tier 3 #1), DEC-387 (FREED), DEC-388 (alert observability architecture, MATERIALIZES at S5e — backend layer now complete + ready for Tier 3 #2 seal)

---

## Tier 3 #2 — COMPLETE (Phase Boundary Resolved)

**Tier 3 #2 architectural review** completed 2026-04-28. Verdict: PROCEED with conditions (amended). Verdict artifact at `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended version).

**Outcomes of Tier 3 #2:**

- Backend architecture sealed (no architectural concerns).
- DEC-388 materialization DEFERRED to sprint-close (Pattern B per `protocols/mid-sprint-doc-sync.md` v1.3.0); draft text in verdict.
- DEC-385 unchanged — remains scheduled for sprint-close write per existing plan.
- 9 new DEFs filed (DEF-217 through DEF-225), 7 routed RESOLVED-IN-SPRINT (Impromptus A+B+C + Session 5c), 1 deferred (DEF-222), 1 routed via Session 5c (DEF-220).
- DEF-175 annotated with main.py + set_order_manager motivators.
- Workflow metarepo bumped to v1.3.0 (mid-sprint doc-sync protocol + structural-anchor amendment).

**Conditions for Session 5c entry (NEW — replaces prior "NONE"):**

- Impromptu A landed CLEAR (DEF-217 + DEF-218 + DEF-219 + DEF-224 + DEF-225 RESOLVED-IN-SPRINT).
- Impromptu B landed CLEAR (DEF-221 RESOLVED-IN-SPRINT; end-to-end Databento auto-resolution validated with the DEF-217 fix).

DEF-220 disposition is folded INTO Session 5c (not a precondition for entry).

**Pre-impromptu doc-sync manifest** at `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md` is the mechanical handoff to sprint-close per `protocols/mid-sprint-doc-sync.md` v1.0.0.

---

## Test Tally

| Session | pytest (main) | pytest total | Vitest | Cumulative new tests |
|---|---|---|---|---|
| **Sprint baseline** | 5,080 | 5,124 | 866 | — |
| After S0 | 5,088 (+8) | 5,132 | 866 | +8 |
| After S1a | 5,106 (+18) | 5,150 | 866 | +26 |
| After S1b | 5,121 (+15) | 5,165 | 866 | +41 |
| After S1c | 5,128 (+7) | 5,167 | 866 | +48 |
| After Tier 3 #1 doc-sync | 5,128 (+0) | 5,167 | 866 | +48 |
| After S2a | 5,133 (+5) | 5,172 | 866 | +53 |
| After S2b.1 | 5,139 (+6) | 5,178 | 866 | +59 |
| After S2b.2 | 5,153 (+14) | 5,192 | 866 | +73 |
| After S2c.1 | 5,159 (+6) | 5,198 | 866 | +79 |
| After S2c.2 | 5,163 (+4) | 5,202 | 866 | +83 |
| After DEF-216 hotfix | 5,163 (+0) | 5,202 | 866 | +83 |
| After S2d | 5,169 (+6) | 5,208 | 866 | +89 |
| After S3 | 5,174 (+5) | 5,213 | 866 | +94 |
| After S4 (operator-local) | 5,184 (+10) | 5,223 | 866 | +104 |
| After S5a.1 | 5,202 (+18) | 5,241 | 866 | +122 |
| After S5a.2 | 5,222 (+20) | 5,261 | 866 | +142 |
| After S5b | 5,232 (+10) | 5,271 | 866 | +152 |
| After Impromptu A | 5,237 (+5) | 5,276 | 866 | +157 |
| **After Impromptu B** | **5,238 (+1)** | **5,277** | **866** | **+158** |

**Sprint cumulative delta:** +158 pytest (operator-local frame), 0 Vitest.

**Bookkeeping discipline note:** S5a.2 + S5b + Impromptu A + Impromptu B closeouts cited tests_added matching actual delta (4 consecutive sessions); S5a.1's +21 vs +18 cosmetic discrepancy was a one-off and the RULE-038 sub-bullet feedback was internalized cleanly.

**Test_main.py baseline drift:** Pre-existing 27 pass / 5 skip / 12 fail. Documented in CLAUDE.md DEF-048 lineage.

**ADMINISTRATIVE NOTE:** CLAUDE.md test count baseline still cites `5,080`; actual operator-local now 5,238. Sprint-end doc-sync MUST refresh.

---

## DECs

### Materialized

| DEC | Description | Sessions | Status |
|---|---|---|---|
| **DEC-386** | OCA-Group Threading + Broker-Only Safety (4-layer architecture) | 0+1a+1b+1c | **Written** to `docs/decision-log.md` post-Tier-3-#1 |
| **DEC-385** | Side-Aware Reconciliation Contract (6-layer architecture) | 2a+2b.1+2b.2+2c.1+2c.2+2d | MATERIALIZED at S2d; will be written to `docs/decision-log.md` at sprint-end |

### Reserved (not yet materialized)

| DEC | Description | Sessions | Materializes at |
|---|---|---|---|
| DEC-388 | Alert observability architecture (resolves DEF-014). Backend complete at S5b; hardening complete after Impromptus A+B+C; frontend complete at S5e. Cross-references DEFs being resolved IN-SPRINT (DEF-217/218/219/220/221/223/224/225) plus deferred DEF-222 + DEF-014. | 5a.1+5a.2+5b + Impromptus A+B+C + 5c+5d+5e | **Sprint-close (Pattern B per `protocols/mid-sprint-doc-sync.md` v1.3.0)** — was Tier 3 #2; deferred per Tier 3 #2 amended verdict 2026-04-28 |

### Freed

| DEC | Reason |
|---|---|
| DEC-387 | Reserved during planning but not consumed; freed at Tier 3 #1 close |

---

## DEFs

### Filed during Sprint 31.91

| DEF | Source | Description | Disposition | Routed to |
|---|---|---|---|---|
| **DEF-209** (extended) | Tier 3 #1 + S4 verification | `Position.side` AND `ManagedPosition.redundant_exit_observed` persistence | Sprint 35+ horizon | Sprint 35+ |
| **DEF-211** (extended) | Pre-existing + Apr 27 Findings 3+4 | EXTENDED scope: D1+D2+D3 | Sprint 31.93 (sprint-gating) | Sprint 31.93 |
| **DEF-212** | Tier 3 #1 Concern B | `_OCA_TYPE_BRACKET = 1` constant drift risk | Sprint 31.92 | Sprint 31.92 |
| **DEF-213** | Tier 3 #1 Concern C | `SystemAlertEvent.metadata` schema gap. **FULLY RESOLVED** | Mark RESOLVED in CLAUDE.md at sprint-end | RESOLVED |
| **DEF-214** | Apr 27 debrief Finding 1 | EOD verification timing race + side-blind classification. **RESOLVED at S5a.1** | Mark RESOLVED in CLAUDE.md at sprint-end | RESOLVED |
| **DEF-215** | Apr 27 debrief Finding 2 | Reconciliation per-cycle log spam | DEFERRED with sharp revisit trigger | Deferred |
| **DEF-216** | S2c.2 CI failure | `test_get_regime_summary` ET-midnight rollover race | RESOLVED in impromptu hotfix `c36a30c` | Mark RESOLVED in CLAUDE.md at sprint-end |
| **DEF-208** | S4 spec Phase D Item 1 grep | Live-trading test fixture missing | Filed; routed for future session | Future session |
| **DEF-217** | Tier 3 #2 Concern A | Databento dead-feed alert_type producer/consumer string mismatch (HIGH severity correctness defect; MUST land before live) | **RESOLVED-IN-SPRINT (Impromptu A, anchor `e78a994`)** — claim applied at sprint-close per `pre-impromptu-doc-sync-manifest.md`. Production-path E2E validation added by Impromptu B (anchor `8efa72e`); now has dual-layer regression coverage (static AST + dynamic E2E) | Sprint 31.91 Impromptu A (LANDED) + Impromptu B cross-validation (LANDED) |
| **DEF-218** | Tier 3 #2 Concern D | `eod_residual_shorts` + `eod_flatten_failed` missing from policy table | **RESOLVED-IN-SPRINT (Impromptu A, anchor `e78a994`)** — claim applied at sprint-close | Sprint 31.91 Impromptu A (LANDED) |
| **DEF-219** | Tier 3 #2 Concern B | Policy table exhaustiveness regression guard not test-enforced | **RESOLVED-IN-SPRINT (Impromptu A, anchor `e78a994`)** — claim applied at sprint-close | Sprint 31.91 Impromptu A (LANDED) |
| **DEF-220** | Tier 3 #2 Concern C / Item 4 | `acknowledgment_required_severities` field has no consumer (wire vs remove disposition) | OPEN — Session 5c | Sprint 31.91 Session 5c |
| **DEF-221** | Tier 3 #2 Concern F / Item 7 | `DatabentoHeartbeatEvent` producer wiring (data-layer health poller) | **RESOLVED-IN-SPRINT (Impromptu B, anchor `8efa72e`)** — claim applied at sprint-close per `pre-impromptu-doc-sync-manifest.md` | Sprint 31.91 Impromptu B (LANDED) |
| **DEF-222** | Tier 3 #2 Item 2 | Predicate-handler subscribe-before-rehydrate audit when producers land | DEFERRED — sprint-gating | Producer-wiring sprint TBD |
| **DEF-223** | Tier 3 #2 Item 8 | Migration framework adoption sweep across 7 other separate DBs | OPEN — Impromptu C | Sprint 31.91 Impromptu C |
| **DEF-224** | Tier 3 #2 Concern E | Duplicate `_AUDIT_DDL` between routes layer and migration framework | **RESOLVED-IN-SPRINT (Impromptu A, anchor `e78a994`)** — claim applied at sprint-close | Sprint 31.91 Impromptu A (LANDED) |
| **DEF-225** | Tier 3 #2 Item 1 | `ibkr_auth_failure` dedicated E2E auto-resolution test | **RESOLVED-IN-SPRINT (Impromptu A, anchor `e78a994`)** — claim applied at sprint-close | Sprint 31.91 Impromptu A (LANDED) |

### Filed pre-Sprint 31.91, status changes

| DEF | Status |
|---|---|
| DEF-204 | All architectural layers LIVE post-S3 + falsifiable validation gate LIVE post-S4. Empirical validation pending at first OCA-effective paper session (Apr 28+) |
| DEF-014 | **Alert observability gap — producer side RESOLVED at S5b** (2 IBKR emitters wired). Backend layer COMPLETE (5a.1 + 5a.2 + 5b). FULL DEF-014 closure at Session 5e (frontend banner + toast + Observatory panel) |
| DEF-158 | Flatten retry side-blindness — RESOLVED in S3. Mark RESOLVED at sprint-end |
| DEF-177 | `RejectionStage` enum missing distinct values — overload `"risk_manager"`; cleanup gated to dedicated cross-domain session |
| DEF-199 | EOD Pass 2 A1 fix preserved — UNCHANGED across S0–S5b |

### Anticipated but NOT filed

| Anticipated DEF | Reason not filed |
|---|---|
| DEF-210 | Referenced in S4 live-enable Gate 3 deferral note for disconnect-reconnect → Sprint 31.93 |

---

## Risks Filed

| RSK | Description | Time-bounded by |
|---|---|---|
| **RSK-DEC-386-DOCSTRING** | `reconstruct_from_broker()` STARTUP-ONLY contract is a docstring, not a runtime gate | Sprint 31.93 DEF-211 D1 |

---

## Resolved Carry-Forward Items (Cumulative)

| Resolved | Resolution session | Detail |
|---|---|---|
| Invariant 21 grep-guard | S1a | LANDED |
| `Order.oca_group_id` field arrival | S1a | LANDED |
| `ManagedPosition.oca_group_id` persistence | S1a | LANDED |
| Defensive Error 201 on T1/T2 submission preserving DEC-117 | S1a | LANDED |
| Caller-side ERROR log suppression on OCA-filled | S1b | RESOLVED |
| Phase D Item 2 (EOD Pass 2 cancel-timeout failure-mode docs + test 7) | S1c | RESOLVED |
| Broker-only path routing through `cancel_all_orders(symbol, await_propagation=True)` | S1c | RESOLVED |
| `reconstruct_from_broker` docstring update | S1c | RESOLVED |
| `_OCA_TYPE_BRACKET` doc-sync paragraph for `live-operations.md` | Tier 3 #1 doc-sync | LANDED |
| Per-session register discipline formalized in workflow metarepo | S2a | LANDED |
| **DEF-213 schema-extension half** | S2b.1 (PARTIAL) | `SystemAlertEvent.metadata` field added |
| 2b.2 cross-component coupling on `_broker_orphan_last_alerted_cycle` | S2b.2 | `HealthMonitor._order_manager` reads dict via `getattr` defensive pattern |
| Spec invariant 8 wrong attribution | S2b.2 | Disclosed and reconciled per RULE-038 |
| **DEF-216** ET-midnight rollover flake | Impromptu hotfix `c36a30c` | Anchor all snapshot timestamps + query date to noon ET |
| Phase D pre-applied operator decision L3 | S2d | Aggregate at ≥10 + per-symbol always fire |
| **DEC-385 materialization** | S2d | Side-aware reconciliation contract complete |
| B22 runbook for `live-operations.md` | S2d | 7 subsections landed in-sprint |
| Architecture catalog `**reconciliation**` block | S2d | Added at `docs/architecture.md:1945-1949` |
| **DEF-158 closure** | S3 | 3-branch side-aware gate |
| `phantom_short_retry_blocked` alert taxonomy | S3 | New CRITICAL alert type |
| OCA-EXEMPT comment refresh for `_check_flatten_pending_timeouts` | S3 | `# OCA-EXEMPT:` regression-guard marker preserved |
| HIGH #4 decomposed live-enable gate | S4 | 3 gates per HIGH #4 |
| Mass-balance assertion at session debrief (Sprint Invariant 17) | S4 | Script + 7 tests + run against real Apr 24 log |
| Spike script freshness (Sprint Invariant 22) | S4 | Parser + ISO-with-dashes |
| Phase 7.4 slippage watch | S4 | Inserted into `market-session-debrief.md` |
| B28 spike trigger registry | S4 | `live-operations.md` restructured |
| Item 7 three-source filename standardization | S4 | All 3 load-bearing surfaces use ISO-with-dashes |
| Item 1 (debrief_export consumer grep) | S4 | Verified zero current consumers |
| Item 4 (mass-balance precedence) | S4 | Implemented |
| **DEF-204 falsifiable validation gate** | S4 | IMSR replay + mass-balance script |
| **DEF-213 atomic-migration half** | S5a.1 | 2 pre-existing emitters migrated. **DEF-213 FULLY RESOLVED** |
| **DEF-214** | S5a.1 | Requirement 0.5 — EOD flatten verification fixed |
| HealthMonitor consumer subscription wiring | S5a.1 | `SystemAlertEvent` handler + `event_bus.subscribe()` |
| `AlertsConfig` Pydantic model + YAML stanza | S5a.1 | New model in both YAMLs |
| Alerts REST routes | S5a.1 | New `argus/api/routes/alerts.py`; 3 endpoints JWT-gated |
| `alert_acknowledgment_audit` SQLite table | S5a.1 | New table; idempotent DDL |
| 5 EOD emission paths distinct | S5a.1 | Side-aware classification |
| All 11 emitter sites populate `metadata` (DEF-213 atomic-migration COMPLETE) | S5a.1 | 13 sites total post-S5a.1 |
| Architecture catalog `**alerts**` block | S5a.1 | Added; freshness gate passes |
| **F2 (S5a.1) — `get_archived_alert_by_id` O(N) linear scan** | S5a.2 | Replaced with SQLite-indexed query |
| **F3 (S5a.1) — In-memory state loss on restart** | S5a.2 | `alert_state` table + `rehydrate_alerts_from_db()` |
| **F4 (S5a.1) — Fire-and-forget event dispatch** | S5a.2 | Persistence-on-consume pattern |
| `auto_resolved` test scaffolding (S5a.1 carry-forward) | S5a.2 | No longer needed — real predicates fire |
| `prior_engagement_source` becomes lookup post-S5a.1 | S5a.2 (partial) | Threshold provider injection |
| WebSocket fan-out (`/ws/v1/alerts`) | S5a.2 | New `argus/api/websocket/alerts_ws.py`; 4 message types |
| Auto-resolution policy table for all 8 alert types | S5a.2 | `argus/core/alert_auto_resolution.py` with 8 predicates + `NEVER_AUTO_RESOLVE` sentinel |
| `phantom_short` predicate single-source-of-truth coupling with S2c.2 threshold | S5a.2 | `threshold_provider` injection |
| Migration framework for `data/operations.db` | S5a.2 | First time in ARGUS |
| `schema_version` table | S5a.2 | Migration framework version tracking |
| Architecture catalog WebSocket table updated | S5a.2 | Catalog freshness gate passes |
| **S5b — IBKR emitter TODOs (DEF-014 producer side)** | S5b | 2 emitters wired at `_reconnect()` end-of-retries (`ibkr_disconnect`) + `_on_error()` CRITICAL non-connection else-branch (`ibkr_auth_failure`) |
| **S5b — E2E pipeline tests (full coverage matrix)** | S5b | 10 new tests in `tests/integration/test_alert_pipeline_e2e.py`; 5 emitter types fully covered + 1 acknowledged gap |
| **S5b — Behavioral Alpaca anti-regression** (MEDIUM #13) | S5b | `tokenize`-based filter (refined from literal substring per Judgment Call 2) |
| **S5b — DEF-014 producer side** | S5b | IBKR producer side complete; full DEF-014 closure at S5e (frontend) |
| **Impromptu A — DEF-217 (HIGH severity producer/consumer string mismatch)** | Impromptu A | One-line fix at `databento_data_service.py:281`; production auto-resolution path now active for Databento dead-feed alerts; pre-fix policy table entry was DEAD CODE |
| **Impromptu A — DEF-218 (`eod_residual_shorts` + `eod_flatten_failed` missing from policy table)** | Impromptu A | Two `NEVER_AUTO_RESOLVE` `PolicyEntry` rows added to `build_policy_table()`; both producers already emit since S5a.1 — they were sitting ACTIVE indefinitely with no policy coverage. Policy table: 8 → 10 entries |
| **Impromptu A — DEF-219 (policy-table exhaustiveness regression guard)** | Impromptu A | New `tests/api/test_policy_table_exhaustiveness.py` (4 tests); AST-based scan of `argus/` for `SystemAlertEvent(alert_type=<literal>)` constructions; mental-revert of DEF-217 fix confirms guard fails on drift |
| **Impromptu A — DEF-224 (duplicate `_AUDIT_DDL` cleanup)** | Impromptu A | `_AUDIT_DDL`, `_AUDIT_INDEX_*`, `_ensure_audit_table`, and 4 call sites deleted from routes layer; migration framework at `argus/data/migrations/operations.py` migration v1 sole owner |
| **Impromptu A — DEF-225 (`ibkr_auth_failure` dedicated E2E test)** | Impromptu A | New `TestE2EIBKRAuthFailureAutoResolution` exercises `OrderFilledEvent` clearing leg of `_ibkr_auth_success_predicate`; closes S5b pipeline-coverage matrix symmetry gap |
| **Impromptu B — DEF-221 (`DatabentoHeartbeatEvent` producer wiring)** | Impromptu B | New `_heartbeat_publish_loop` task wired into `DatabentoDataService.start()` / `stop()`; suppression contract via existing `_stale_published` (no new state attribute introduced); configurable via `DatabentoConfig.heartbeat_publish_interval_seconds` (`gt=0.0, le=300.0`); E2E test validates full pipeline with falsifiable suppression assertion |
| **Impromptu B — DEF-217 dual-layer regression coverage** | Impromptu B | New `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer` is the FIRST E2E test that drives the production Databento emitter chain (vs fabricating `SystemAlertEvent`); assertion `alert_type == "databento_dead_feed"` is the dynamic regression guard alongside Impromptu A's static AST guard. Mental-revert proven: regression in either direction trips both guards |
| **Impromptu B — DEF-221 suppression contract** | Impromptu B | `if self._stale_published: continue` branch enforced; mental-revert proven (test asserts `len(heartbeats) == heartbeats_before_recovery` across ~5-interval observation window) |

---

## Outstanding Code-Level Items (Sprint-Tracked, Not DEF-Worthy)

| Item | Severity | Source | Notes |
|---|---|---|---|
| `asyncio.get_event_loop().time()` in IBKR polling loop | LOW | S0 | Cleanup deferred until Python floor bumps to 3.12+ |
| DISCOVERY line-number anchors drifted >5 lines from spec | LOW | S1a | C6 soft halt |
| Generic Error 201 logged at WARNING | LOW (accepted) | S1a | Pre-Sprint-31.91 baseline |
| Simultaneous-multiple-positions-same-symbol OCA edge case | OBSERVATIONAL | S1a | Naturally handled |
| Latent rollback-flag inconsistency under `bracket_oca_type=0` | INFORMATIONAL | S1b JC2 | Bounded by RESTART-REQUIRED note |
| Revision-rejected fresh T1/T2 resubmissions outside original bracket OCA group | LOW (cleanup-eligible) | S1b Follow-Up #4 | Bracket OCA covers normal operation |
| Failure-mode docs for `live-operations.md` "Phantom-Short Gate Diagnosis and Clearance" | RESOLVED in S2d (B22) | S1c | Sprint-end doc-sync verify presence |
| B5-MILD line shift — call site `:1505-1535` spec → `:1519-1553` post-edit | LOW (acceptable) | S2a | No spec adjustment needed |
| EventBus dispatch async-via-`asyncio.create_task`; tests need `_reconcile_and_drain` helper | OBSERVATIONAL | S2b.1 | Pattern matches |
| Cycle 1-2 WARNING is unthrottled but bounded | LOW (acceptable) | S2b.1 | ThrottledLogger compliance reviewed |
| Pass 1 retry SELL detection at `:1777` consistency gap | LOW (consistency gap) | S2b.2 Edge Case 3 | Future session |
| `HealthMonitor.set_order_manager()` production wiring at startup deferred — NOT addressed in S5a.2 or S5b | RULE-007 deferral | S2b.2 Edge Case 1 | Future or Tier 3 #2 may revisit |
| Spec do-not-modify line range `:1670-1750` for `order_manager.py` does NOT actually contain SELL-detection branching | LOW (spec-anchor discrepancy) | S2b.2 RULE-038 #3 + S3 B5-informational + S5b RULE-038 disclosure | Future impl prompts |
| `logger.info` breakdown lines on margin reset site previously absent | INFORMATIONAL | S2b.2 Edge Case 4 | No existing log-line assertion picks them up |
| Persistence failure leaves disk state stale until restart re-detection | LOW (documented contract) | S2c.1 review concern #1 | DEC-345 fire-and-forget |
| `OrderManager.stop()` does not await `_pending_gate_persist_tasks` | LOW (same-family follow-on) | S2c.1 review concern #2 | NOT addressed across S2d/S3/S4/S5a.1/S5a.2/S5b; eligible for future improvement |
| `rejection_stage="risk_manager"` overload for `phantom_short_gate` | LOW (DEF-177 covers split) | S2c.1 judgment call #4 + review concern #3 | When DEF-177 cross-domain enum work lands |
| `_phantom_short_clear_cycles` not cleared in `reset_daily_state` | LOW (defensible either way) | S2c.2 J-2 | Future alignment session |
| LONG-shares branch not directly exercised by 4 new auto-clear tests | LOW (small coverage gap) | S2c.2 reviewer soft observation #2 | Future test |
| Test 6 anchors on S2c.1's rehydration log not S2d's lifespan log | LOW (small docstring/anchor mismatch) | S2d reviewer soft observation #1 | Behaviorally correct |
| `prior_engagement_source` hardcoded — partially addressed at S5a.2 | LOW (documented inline) | S2d reviewer soft observation #3 | Future session may complete |
| Audit table `phantom_short_override_audit` has no retention policy by design | OBSERVATIONAL (intentional) | S2d reviewer soft observation #4 | Forensic-grade audit log |
| Defensive `try/except` around `event_bus.publish` at Branch 2 marked `# pragma: no cover - defensive` | OBSERVATIONAL (intentional) | S3 reviewer Notable Item #2 | Idiomatic and safe |
| Test 3 (Branch 3) asserts no `SystemAlertEvent` at all | OBSERVATIONAL (intentional defensive) | S3 reviewer Notable Item #3 | Future regression adding an alert to Branch 3 will require deliberate test update |
| Mass-balance script regex doesn't pick up trail/escalation SELL placements | LOW (conservative-correct flagging) | S4 closeout | Operator confirms by symbol-trace |
| `Position closed` log line lacks share count | LOW (test-side reconstruction) | S4 closeout | Not a runtime-code dependency |
| `Order filled:` log line lacks symbol/side | LOW (test/script-side reconstruction) | S4 closeout | Not a runtime-code dependency |
| Item 7 historical references in HISTORICAL/FROZEN docs preserve compact-YYYYMMDD or Unix-epoch | OBSERVATIONAL (intentional preservation) | S4 reviewer Focus Area 6 minor | Future opportunistic doc-hygiene pass |
| Mass-balance script flags 195 `unaccounted_leak` rows on Apr 24 cascade log | EXPECTED (validation surface) | S4 closeout | Apr 24 IS the known-bad cascade reference |
| CLAUDE.md test count baseline still cites `5,080` | ADMINISTRATIVE | S4 closeout RULE-038 disclosure | Sprint-end doc-sync MUST refresh |
| Closeout `tests_added: 21` vs actual +18 (S5a.1 only) | COSMETIC (resolved) | S5a.1 reviewer F1 | RULE-038 sub-bullet feedback internalized at S5a.2 + S5b |
| EOD verify polling residual_shorts last-snapshot semantics could merit inline comment | COSMETIC | S5a.1 reviewer F7 | Optional doc-hygiene |
| Alerts REST routes have no rate limiting (JWT-only) | ACCEPTABLE | S5a.1 reviewer F8 | Per-route throttle if alert volume escalates |
| Predicate-handler subscriptions wired before rehydration completes (no realistic race today) | INFORMATIONAL | S5a.2 reviewer F1 | When producers land, defer `_subscribe_predicate_handlers()` to AFTER rehydration |
| Duplicate `_AUDIT_DDL` in `argus/api/routes/alerts.py` (S5a.1 leftover) | LOW (cleanup) | S5a.2 reviewer F2 | Future cleanup |
| Best-effort SQLite write with WARNING-only log on failure for alert persistence | LOW (consistent with DEC-345 fire-and-forget) | S5a.2 reviewer F3 | Aligned with `EvaluationEventStore` pattern |
| `_evaluate_predicates` broad exception catch on predicate body | DEFENSIVE (reasonable) | S5a.2 reviewer F4 | Production code defensively catching one bad predicate |
| `routes/alerts.py` post-commit persistence path swallows exceptions in defensive try | DEFENSIVE (reasonable) | S5a.2 reviewer F5 | Defense-in-depth |
| New event dataclasses are deferred-emission (acknowledged) | DOCUMENTED | S5a.2 reviewer F6 | When producers land, deferred-emission docstring should be updated |
| **NEW (S5b):** `ibkr_auth_failure` E2E auto-resolution test gap (structurally covered by Test 4) | LOW | S5b closeout matrix gap analysis + reviewer F2 | Acceptable; future dedicated test would add coverage but no new structural verification. Tier 3 #2 to validate gap closure |
| **NEW (S5b):** Refined behavioral Alpaca check (tokenize-based) | MINOR_DEVIATION (reviewer-accepted) | S5b Judgment Call 2 + reviewer F1 | Necessary to satisfy do-not-modify constraint; architectural intent preserved |
| **NEW (S5b):** Conftest mock updates kept local rather than shared (Judgment Call 3) | DEFENSIVE (reasonable) | S5b closeout Judgment Call 3 | Avoids regression in 25+ unrelated tests |
| **NEW (S5b):** `phantom_short_startup_engaged` 24h-elapsed branch isn't end-to-end here | LOW | S5b closeout matrix gap analysis | Tracked as recommended future test |
| **NEW (S5b):** Conftest fixture duplication ~50 LOC between new E2E file and `tests/execution/test_ibkr_broker.py` (intentional per Judgment Call 3) | LOW (cleanup-eligible) | S5b closeout | Future test-hygiene session |
| **NEW (S5b):** Stale line-number references in spec for IBKR (`:453` actual `~:570`; `:531` actual `~:416-420`) | LOW (acknowledged) | S5b RULE-038 disclosures | Future impl prompts should reference structural anchors |
| **NEW (Impromptu A):** Test-side `_migrate_operations_db` helper added to keep 4 `_seed_alert`-based route tests passing post-DEF-224 | MINOR_DEVIATION (reviewer-accepted) | Impromptu A Closeout Judgment Call 1 + reviewer F3 | Path A taken; architectural intent preserved (migration framework canonical home); production-vs-test asymmetry made explicit |
| **NEW (Impromptu A):** DEF-219 guard 4th sanity test (`test_argus_root_resolves`) | MINOR_DEVIATION (reviewer-accepted) | Impromptu A Closeout Judgment Call 2 + reviewer F1 | 3-line defensive infrastructure prevents silent false-passes if `argus/` unreachable from test path; reviewer recommends keeping |
| **NEW (Impromptu A):** Mid-impromptu `/private/tmp` ENOSPC briefly blocked Bash | INFO (resolved) | Impromptu A reviewer F2 | Operator freed disk; suite completed clean on retry |
| **NEW (Impromptu B):** Recovery transition tested via direct state manipulation rather than driving `_stale_data_monitor` flow | LOW (TEST_COVERAGE_GAP) | Impromptu B reviewer Concern 1 + closeout JC3 | Future test-hygiene could add Stale→Resumed-via-monitor variant; predicate's `DataResumedEvent` branch covered elsewhere by unit-level tests + existing `TestE2EDatabentoDeadFeed` |
| **NEW (Impromptu B):** Pre-existing `_log_post_start_symbology_size` task untracked by `start()`/`stop()` (`databento_data_service.py:392`) — `Task was destroyed but it is pending!` warning in test teardown | LOW (OTHER, pre-existing) | Impromptu B reviewer Concern 2 | Out of scope for Impromptu B; sibling-class candidate for DEF-202 (long-lived task lifecycle hygiene) in future component-ownership cleanup |
| **NEW (Impromptu B):** Suppression test depends on `start()` not resetting `_stale_published` | INFO (TEST_COVERAGE_GAP) | Impromptu B reviewer Concern 3 | Production-side docstring is canonical guard; no test-side guard needed |

---

## Carry-Forward Watchlist (Active)

| Item | Status | Lands in |
|---|---|---|
| **Tier 3 #2 architectural review** | ✅ COMPLETE 2026-04-28; Lands in: pre-impromptu doc-sync (this commit) | Pre-impromptu doc-sync (this commit) |
| **Daily-flatten cessation** | Conservative criteria #1 + #2 + #3 SATISFIED post-S4; criteria #4 + #5 pending | Sprint-end + 5 paper-session-clean window |
| Operator daily-flatten | REQUIRED, NOT OPTIONAL | Active until criterion #5 |
| Banner mount on `Dashboard.tsx` (5c) | Watch | 5e (relocate to `Layout.tsx`) |
| Toast mount on `Dashboard.tsx` (5d) | Watch | 5e (relocate to `Layout.tsx`) |
| `/api/v1/alerts/{id}/audit` endpoint surface | Watch — verify whether separate `/audit` endpoint still needed | 5e (consume) |
| AlpacaBroker `_check_connected` AttributeError | DISCLOSED | Sprint 31.94 |
| `BracketOrderResult.oca_group_id` exposure | OBSERVATIONAL | Future |
| Tier 3 #1 Concern A (helper relocation) | Implicit DEF-212 sibling | Sprint 31.92 |
| Tier 3 #1 Concerns E + F (test-hygiene) | Backlog | Future |
| **First OCA-effective paper session debrief** | Watch (Apr 28+) | First post-`bf7b869` paper session |
| **First post-S4 paper-session mass-balance run** | Watch | Operator runs `validate_session_oca_mass_balance.py` |
| `HealthMonitor.set_order_manager()` production wiring at startup | NOT addressed across S5a.1/S5a.2/S5b | Future or Tier 3 #2 may revisit |
| Spec do-not-modify anchor for `order_manager.py` should reference structural rather than line-number anchors | TRACKED | Future impl prompts |
| `OrderManager.stop()` graceful-shutdown await of `_pending_gate_persist_tasks` | Watch | NOT addressed in any post-S2c.1 session; eligible for future improvement |
| `_phantom_short_clear_cycles` reset_daily_state symmetry | Watch | Future alignment session |
| LONG-shares-clearing test coverage gap (S2c.2) | Watch | Future session |
| `prior_engagement_source` becomes lookup post-S5a.1 — partially addressed at S5a.2 | Watch | Future session may complete |
| S2d-specific test for lifespan-layer startup log | LOW priority | Future test-hygiene session |
| Two pre-existing operator stashes (`stash@{0}`, `stash@{1}`) | OPERATOR ACTION | At operator's convenience |
| Original Pass 1 retry SELL consistency gap at `:1777` | OBSERVATIONAL | Future session |
| Mass-balance script regex extension for trail/escalation paths | LOW priority | Future session |
| Item 7 historical doc references in frozen artifacts | OBSERVATIONAL | Opportunistic doc-hygiene pass |
| **CLAUDE.md test count baseline refresh** (currently `5,080`; actual operator-local 5,238) | ADMINISTRATIVE | Sprint-end doc-sync |
| **`ReconciliationCompletedEvent` producer wiring** (deferred-emission) | DEFERRED | post-31.9 component-ownership sprint |
| **`IBKRReconnectedEvent` producer wiring** (deferred-emission) | DEFERRED | `post-31.9-reconnect-recovery` sprint (DEF-194/195/196) |
| **Doc-sync sweep check** for deferred-emission docstrings | LOW priority | Future tooling |
| **NEW (S5b):** `phantom_short_startup_engaged` 24h-elapsed branch E2E (would require time-mocking inside the predicate) | LOW | Future test-hygiene session |
| **NEW (S5b):** Conftest fixture duplication ~50 LOC | LOW (cleanup-eligible) | Future test-hygiene session |
| **DEF-217** Databento alert_type mismatch fix | ✅ **RESOLVED-IN-SPRINT (Impromptu A, anchor `e78a994`)** + dual-layer regression coverage via Impromptu B (anchor `8efa72e`) | Sprint-close transitions claim per `pre-impromptu-doc-sync-manifest.md` |
| **DEF-218** EOD policy table additions | ✅ **RESOLVED-IN-SPRINT (Impromptu A, anchor `e78a994`)** | Sprint-close transitions claim |
| **DEF-219** Policy table exhaustiveness regression guard | ✅ **RESOLVED-IN-SPRINT (Impromptu A, anchor `e78a994`)** | Sprint-close transitions claim |
| **DEF-220** `acknowledgment_required_severities` disposition | OPEN — Session 5c (NEXT) | Sprint 31.91 in-sprint resolution |
| **DEF-221** `DatabentoHeartbeatEvent` producer wiring | ✅ **RESOLVED-IN-SPRINT (Impromptu B, anchor `8efa72e`)** | Sprint-close transitions claim |
| **DEF-222** Predicate-handler subscribe-before-rehydrate audit | DEFERRED — gated on future producers | Producer-wiring sprint TBD |
| **DEF-223** Migration framework adoption sweep | OPEN — Impromptu C | Sprint 31.91 in-sprint resolution |
| **DEF-224** Duplicate `_AUDIT_DDL` cleanup | ✅ **RESOLVED-IN-SPRINT (Impromptu A, anchor `e78a994`)** | Sprint-close transitions claim |
| **DEF-225** `ibkr_auth_failure` dedicated E2E test | ✅ **RESOLVED-IN-SPRINT (Impromptu A, anchor `e78a994`)** | Sprint-close transitions claim |
| Workflow metarepo amendment v1.2.0 → v1.3.0 | ✅ COMPLETE 2026-04-28 | claude-workflow repo (separate flow) |

---

## Pre-Applied Operator Decisions (Re-stated for self-containment)

| # | Decision | Lands In |
|---|---|---|
| Phase D Item 2 | EOD Pass 2 cancel-timeout failure-mode docs + test 7 | Session 1c (RESOLVED) |
| Phase D Item 3 | Health + broker-orphan double-fire dedup → Option C hybrid | Session 2b.2 (RESOLVED) |
| M4 cost-of-error asymmetry | Auto-clear threshold default = 5 | Session 2c.2 (RESOLVED) |
| L3 always-fire-both-alerts | Aggregate at ≥10 + per-symbol always fire | Session 2d (RESOLVED) |
| MEDIUM #13 Alpaca anti-regression | `inspect.getsource` check | Session 5b (RESOLVED via tokenize-based refinement) |
| HIGH #1 auto-resolution policy | Explicit per-alert-type predicates (11 alert types covered post-S5b) | S5a.2 + S5b (RESOLVED) |
| HIGH #4 decomposed live-enable gate | 4 criteria | Session 4 (RESOLVED) |

---

## Operator Decisions Log (Mid-Sprint)

### 2026-04-27 — Phase D Item 6: Interim Merge Timing → Option C

merge after 1c (already done); KEEP operator daily flatten as belt-and-suspenders.

### 2026-04-27 — Daily-Flatten Cessation Criteria → Conservative

Daily-flatten continues until ALL of:
1. ✅ Session 2d landed and CLEAR (SATISFIED 2026-04-28)
2. ✅ Session 3 landed and CLEAR (SATISFIED 2026-04-28)
3. ✅ Session 4 landed and CLEAR (SATISFIED 2026-04-28)
4. ❌ Sprint 31.91 sealed (pending — needs Tier 3 #2 + S5c/d/e + doc-sync)
5. ❌ 5 paper sessions post-seal showing clean mass-balance + zero broker-orphan SHORTs surviving reconcile (pending)

### 2026-04-27 — `_OCA_TYPE_BRACKET` doc-sync routing → bundle into sprint-end

Already landed in Tier 3 #1 doc-sync per `df48e31`.

### 2026-04-27 — Per-Session Register Discipline → adopt + formalize in metarepo

Workflow metarepo amendment at commit `606934e` (workflow v1.2.0).

### 2026-04-28 — DEF-216 fix-now decision → impromptu hotfix between S2c.2 and S2d

Operator chose to fix the ET-midnight rollover flake immediately. Hotfix landed in `c36a30c`.

---

## Apr 27 Paper-Session Debrief Findings (Folded into Tier 3 #1 doc-sync)

**CRITICAL FRAMING:** Apr 27 ran on a pre-`bf7b869` commit. **First OCA-effective paper session is Apr 28 or later.**

| Finding | Routing |
|---|---|
| Finding 1 — EOD verification timing race + side-blind classification | DEF-214; **RESOLVED at S5a.1** |
| Finding 2 — Reconciliation per-cycle log spam | DEF-215; deferred with sharp revisit trigger |
| Finding 3 — `max_concurrent_positions` counts broker-only longs | Folded into DEF-211 extended scope (D3) |
| Finding 4 — Boot-time reconciliation policy + IMPROMPTU-04 gate | Folded into DEF-211 extended scope (D2 + D3) |

---

## Tier 3 Reviews

### Tier 3 #1 — PROCEED (2026-04-27)

- **Anchor commit:** `bf7b869` on `main`
- **Combined-diff scope:** Sessions 0+1a+1b+1c (OCA architecture track)
- **Verdict artifact:** `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md` (commit `df48e31`)
- **Outcomes:** DEC-386 written; DEFs 209/211/212/213/214/215 filed; RSK-DEC-386-DOCSTRING filed; Session 5a.1 impl prompt amended; 10 doc files updated

### Tier 3 #2 — PENDING (Sprint Phase Boundary)

- **Anticipated anchor:** Sessions 5a.1 + 5a.2 + 5b (combined diff already on `main`)
- **Combined-diff base SHA:** `5f6b2a6` per S5b closeout pre-amble
- **Tier 3 track marker on closeouts:** `alert-observability` (S5a.1 + S5a.2 + S5b set this marker)
- **Expected scope of review:**
  - HealthMonitor consumer + REST + acknowledgment (5a.1)
  - Persistence + auto-resolution policy + WS fan-out + migration framework (5a.2)
  - IBKR emitter wiring + E2E pipeline coverage matrix (5b)
  - Cross-cutting concerns: 6 `main.py` scoped exceptions in this sprint; 3 deferred-emission events; predicate-handler subscribe-before-rehydrate observation; `acknowledgment_required_severities` gate consumer wiring still pending; `ibkr_auth_failure` E2E gap; `HealthMonitor.set_order_manager()` production wiring still pending

---

## Emitter-Site Tracking (FINAL — Sprint 31.91 emitter scope COMPLETE)

All 15 alert-emission sites populate `metadata`:

| # | Site | File | Source session | Migrated at |
|---|---|---|---|---|
| 1 | Databento dead-feed (`max_retries_exceeded`) | `argus/data/databento_data_service.py:279-296` | Pre-Sprint-31.91 | S5a.1 |
| 2-4 | `_emit_cancel_propagation_timeout_alert` (3 invocations) | `argus/execution/order_manager.py:2333-2356` | S1c | S5a.1 |
| 5 | `_handle_broker_orphan_short` (`phantom_short`) | `argus/execution/order_manager.py:2381` | S2b.1 | S2b.1 |
| 6 | `_handle_broker_orphan_long` (`stranded_broker_long`) | `argus/execution/order_manager.py:2204+` | S2b.1 | S2b.1 |
| 7 | Health integrity-check `phantom_short` | `argus/core/health.py:548` | S2b.2 | S2b.2 |
| 8 | EOD Pass 2 `phantom_short` | `argus/execution/order_manager.py:1958` | S2b.2 | S2b.2 |
| 9 | Aggregate `phantom_short_startup_engaged` | `argus/main.py:1098-1120` | S2d | S2d |
| 10 | Per-symbol `phantom_short` from startup rehydration | `argus/main.py:1130` | S2d | S2d |
| 11 | `phantom_short_retry_blocked` (DEF-158 retry) | `argus/execution/order_manager.py:3293-3314` | S3 | S3 |
| 12 | `eod_residual_shorts` (severity warning) | `argus/execution/order_manager.py:1995-2087` | S5a.1 | S5a.1 |
| 13 | `eod_flatten_failed` (severity critical) | `argus/execution/order_manager.py:1995-2087` | S5a.1 | S5a.1 |
| **14** | **`ibkr_disconnect`** (reconnect-failure) | `argus/execution/ibkr_broker.py:633-662` | **S5b** | **S5b** |
| **15** | **`ibkr_auth_failure`** (CRITICAL non-connection) | `argus/execution/ibkr_broker.py:453-497` (helper at `:422-434` call site) | **S5b** | **S5b** |

**15 alert-emission sites total post-S5b. All populate `metadata` from day one.**

**11 distinct alert types covered by S5a.2 auto-resolution policy table:**
- `phantom_short` (3 sources; severity `critical`)
- `phantom_short_retry_blocked` (1 source; severity `critical`) — `NEVER_AUTO_RESOLVE`
- `phantom_short_startup_engaged` (1 source; severity `critical`)
- per-symbol `phantom_short` from startup rehydration (1 source; severity `critical`)
- `stranded_broker_long` (1 source; severity `warning`)
- `eod_residual_shorts` (1 source; severity `warning`)
- `eod_flatten_failed` (1 source; severity `critical`)
- `cancel_propagation_timeout` (3 invocations) — `NEVER_AUTO_RESOLVE`
- `databento_dead_feed` (1 source) — auto-resolves on `DatabentoHeartbeatEvent` or `DataResumedEvent`
- `ibkr_disconnect` (1 source) — auto-resolves on `IBKRReconnectedEvent` **NEW S5b**
- `ibkr_auth_failure` (1 source) — auto-resolves on `(OrderFilledEvent, IBKRReconnectedEvent)` **NEW S5b**

---

## SQLite Storage (Sprint 31.91)

| File | Source session | Schema | Purpose |
|---|---|---|---|
| `data/operations.db` | S2c.1 | `phantom_short_gated_symbols` table (5 cols) | Per-symbol entry-gate state |
| `data/operations.db` | S2d | `phantom_short_override_audit` table (8 cols + 2 indexes) | Forensic audit log of operator overrides |
| `data/operations.db` | S5a.1 | `alert_acknowledgment_audit` table (audit_kinds: `ack`, `duplicate_ack`, `late_ack`, `auto_resolution`) | Forensic audit log of alert state transitions |
| `data/operations.db` | S5a.2 | `alert_state` table + 3 indexes | Persisted alert state for restart-recovery |
| `data/operations.db` | S5a.2 | `schema_version` table | Migration framework version tracking |

**5 tables in `data/operations.db` post-Sprint-31.91-backend.** S5b adds no new SQLite surfaces. Sprint-end doc-sync MUST surface all 5 tables.

**Migration framework introduced at S5a.2** (first time in ARGUS): `argus/data/migrations/{__init__,framework,operations}.py`. Migration v1 codifies all S5a.1 + S5a.2 tables.

---

## Validation Infrastructure (Sprint 31.91, S4)

| Surface | File | Purpose |
|---|---|---|
| Mass-balance categorized variance script | `scripts/validate_session_oca_mass_balance.py` (462 LOC) | Consumes `logs/argus_YYYYMMDD.jsonl` |
| IMSR replay integration test | `tests/integration/test_imsr_replay.py` | RULE-051 mechanism-signature anchors |
| Synthetic-fixture mass-balance tests | `tests/scripts/test_validate_session_oca_mass_balance.py` (7 tests) | Coverage of all H2 and Item 4 categorization rules |
| Spike-filename verification tests | `tests/scripts/test_spike_script_filename.py` (2 tests) | Item 7 surgical-fix verification |
| **NEW (S5b):** Alert pipeline E2E tests | `tests/integration/test_alert_pipeline_e2e.py` (10 tests, 881 LOC) | Full pipeline coverage matrix: emitter → REST → WS → ack → audit → auto-resolution → restart-survives |

---

## `main.py` Scoped Exceptions (FINAL — 6 exceptions across sprint)

Per invariant 15, `main.py` is do-not-modify with documented scoped exceptions. Sprint 31.91 has 6 such exceptions:

1. **S2a** — call-site refactor at `:1519-1553`
2. **S2c.1** — rehydration call at `:1066-1080`
3. **S2d** — startup-emission block at `:1078-1141`
4. **S5a.1** — `SystemAlertEvent` subscription at `:431` (8-line block at L411-419 in original)
5. **S5a.2** — HealthMonitor kwargs at `:406-417`
6. **S5a.2** — `rehydrate_alerts_from_db()` at `:425`

S5b zero `main.py` edits. S5c/d/e likely zero `main.py` edits (frontend layer). Tier 3 #2 may want to ratify the scoped-exception accumulation.

---

## Session Order (Sequential — Strict, REVISED post-Tier-3-#2)

1. ✅ Session 0 — CLEAR, commit `9b7246c`
2. ✅ Session 1a — CLEAR, commit `b25b419`
3. ✅ Session 1b — CLEAR, commit `6009397`
4. ✅ Session 1c — CLEAR, commit `49beae2`
5. ✅ **Tier 3 #1** — PROCEED, verdict commit `df48e31`. **DEC-386 materialized.**
6. ✅ Session 2a — CLEAR, commit `813fc3c`
7. ✅ Session 2b.1 — CLEAR, commit `4119608`
8. ✅ Session 2b.2 — CLEAR, commit `a6846c6`
9. ✅ Session 2c.1 — CLEAR, commit `0c034b3`
10. ✅ Session 2c.2 — CLEAR, commit `24320e5`
11. ✅ Impromptu hotfix DEF-216 — CLEAR, commit `c36a30c`
12. ✅ Session 2d — CLEAR, commit `93f56cd`. **DEC-385 materialized in code (write deferred to sprint-close).**
13. ✅ Session 3 — CLEAR, commit `a11c001`. **DEF-158 RESOLVED.**
14. ✅ Session 4 — CLEAR, barrier `da325a0`. **DEF-204 falsifiably validated.**
15. ✅ Session 5a.1 — CLEAR, commit `0236e27`. **DEF-213 + DEF-214 RESOLVED.**
16. ✅ Session 5a.2 — CLEAR, commit `9475d91`.
17. ✅ Session 5b — CLEAR_WITH_NOTES, commit `b324707`. **DEF-014 producer side RESOLVED; backend SEALED.**
18. ✅ **Tier 3 #2** — PROCEED with conditions (amended), verdict commit `<this sync's verdict-amendment commit>`. **9 new DEFs filed, 7 routed in-sprint.**
19. ✅ **Pre-impromptu doc-sync** — this commit; manifest at `pre-impromptu-doc-sync-manifest.md`.
20. ✅ **Impromptu A** (alert observability hardening: DEF-217 + DEF-218 + DEF-219 + DEF-224 + DEF-225) — CLEAR_WITH_NOTES, anchor commit `e78a994` + closeout-SHA-backfill `ad1e7ff`. **DEF-217 (HIGH) + DEF-218 + DEF-219 + DEF-224 + DEF-225 RESOLVED-IN-SPRINT** (transitions applied at sprint-close per `pre-impromptu-doc-sync-manifest.md`).
21. ✅ **Impromptu B** (Databento heartbeat producer + DEF-217 end-to-end validation: DEF-221) — CLEAR, anchor commit `8efa72e`. **DEF-221 RESOLVED-IN-SPRINT** + DEF-217 cross-validated by production-path E2E (transitions applied at sprint-close per `pre-impromptu-doc-sync-manifest.md`).
22. ⏳ **Session 5c** (`useAlerts` hook + Dashboard banner + DEF-220 disposition) — Tier 2 inline. Impl prompt: `sprint-31.91-session-5c-impl.md` (amended). **BOTH CONDITIONS MET: Impromptu A landed CLEAR ✅; Impromptu B landed CLEAR ✅.** ← **NEXT**
23. ⏳ **Impromptu C** (migration framework adoption sweep: DEF-223) — Tier 2 inline. Impl prompt: `sprint-31.91-impromptu-c-migration-framework-sweep-impl.md`.
24. ⏳ Session 5d (toast + acknowledgment UI flow) — unchanged.
25. ⏳ Session 5e (Observatory alerts panel + cross-page integration) — unchanged. **DEF-014 closes here.**
26. ⏳ Sprint-close doc-sync — reads `pre-impromptu-doc-sync-manifest.md` per `protocols/mid-sprint-doc-sync.md` v1.0.0; writes DEC-385 + DEC-388; transitions all RESOLVED-IN-SPRINT DEFs.

---

## Sprint-End Deliverable (Forward-Looking)

When Session 5e clears, the Work Journal produces the doc-sync handoff per `templates/work-journal-closeout.md` v1.4.0 + `templates/doc-sync-automation-prompt.md` v1.2.0. The sprint-close doc-sync reads `pre-impromptu-doc-sync-manifest.md` (per `protocols/mid-sprint-doc-sync.md` v1.0.0) plus all per-session closeout files in the sprint folder; verifies each claimed DEF transition's owning closeout landed CLEAR; applies transitions in manifest-listed order.

**Items the sprint-end doc-sync MUST surface:**

DEC writes:
- DEC-386 documentation (already done in Tier 3 #1 doc-sync; verify)
- **DEC-385 documentation (MATERIALIZED at S2d; deferred-text in Tier 3 #2 verdict; writes at sprint-close per Pattern B)**
- **DEC-388 documentation (materializes at sprint-close per Pattern B; covers S5a.1+S5a.2+S5b+Impromptus A+B+C+S5c+S5d+S5e — extended policy table to 10 entries, regression guard established, route-layer DDL duplication removed, `ibkr_auth_failure` E2E coverage closed, Databento producer wired, migration framework adopted across 7 separate DBs, frontend banner + toast + Observatory panel landed)**

DEF transitions (CLAUDE.md DEF table updates):
- **17 DEFs filed in this sprint integrated into CLAUDE.md** (DEF-208/209/211/212/213/214/215/216 from pre-Tier-3-#2; DEF-217/218/219/220/221/222/223/224/225 from Tier 3 #2)
- DEF-213 marked FULLY RESOLVED (schema half S2b.1 + atomic-migration half S5a.1)
- DEF-214 marked RESOLVED via S5a.1
- DEF-216 marked RESOLVED via impromptu hotfix `c36a30c`
- DEF-158 marked RESOLVED via S3 (commit `a11c001`)
- **DEF-014 marked RESOLVED via S5e** (full closure once frontend lands)
- **DEF-217 marked RESOLVED-IN-SPRINT via Impromptu A** (anchor commit `e78a994`)
- **DEF-218 marked RESOLVED-IN-SPRINT via Impromptu A** (anchor commit `e78a994`)
- **DEF-219 marked RESOLVED-IN-SPRINT via Impromptu A** (anchor commit `e78a994`)
- **DEF-224 marked RESOLVED-IN-SPRINT via Impromptu A** (anchor commit `e78a994`)
- **DEF-225 marked RESOLVED-IN-SPRINT via Impromptu A** (anchor commit `e78a994`)
- DEF-220 marked RESOLVED-IN-SPRINT via Session 5c (anchor TBD)
- DEF-221 marked RESOLVED-IN-SPRINT via Impromptu B (anchor TBD)
- DEF-223 marked RESOLVED-IN-SPRINT via Impromptu C (anchor TBD)
- DEF-208/209/211/212/215/222 dispositions documented (deferred / sprint-gating routing) per Tier 3 #1 + #2 verdicts

Risk register:
- RSK-DEC-386-DOCSTRING in `risk-register.md`

CLAUDE.md:
- Test count baseline refresh (currently `5,080`; actual operator-local 5,237 → final TBD post-S5e)

Architecture.md:
- OCA architecture (already done; verify) + side-aware reconciliation contract per DEC-385 (new) + retry-path side-check section (new, S3) + validation infrastructure layer (S4) + alert observability per DEC-388 (S5a.1+S5a.2+S5b+Impromptus A+B+C+S5c+S5d+S5e)
- Storage table: 5 `data/operations.db` tables + migration framework adoption across 7 other DBs (post-Impromptu C)
- Architecture catalog `**reconciliation**` block (already done in S2d; verify)
- Architecture catalog `**alerts**` block (already done in S5a.1; verify)
- Architecture catalog `**WS /ws/v1/alerts**` block (already done in S5a.2; verify)

Operational docs:
- `live-operations.md` updates: extensive list per S2d/S3/S4/S5a.1/S5a.2/S5b/Impromptu A carry-forwards
- `pre-live-transition-checklist.md` (already done in S4 Part 5a; verify; **DEF-217 closure adds "Databento dead-feed alert auto-resolution validated end-to-end" line per Impromptu B**)
- `protocols/market-session-debrief.md` Phase 7.4 slippage watch (already done in S4; verify)
- Apr 27 debrief findings folded (already done; verify)

Sprint history:
- Sprint-history.md entry for Sprint 31.91 (covers S0–S5e + 1 Tier 3 #1 + 1 Tier 3 #2 + 4 impromptus [DEF-216 hotfix + Impromptus A+B+C] + 1 in-sprint hotfix)

Architectural notes:
- Migration framework adoption note (S5a.2 introduced first migration framework in ARGUS; Impromptu C extended adoption to 7 other separate DBs)
- DEF-204 falsifiable validation gate operational reference (S4)
- 3 deferred-emission events documented (`ReconciliationCompletedEvent`, `IBKRReconnectedEvent`, `DatabentoHeartbeatEvent` — Databento heartbeat producer landed at Impromptu B; the other two remain deferred to producer sprints)
- Tier 3 #2 verdict artifact + amended verdict outcomes
- Policy table exhaustiveness regression guard (DEF-219 / Impromptu A) as the canonical drift-prevention pattern for any future alert_type addition

---

*End Sprint 31.91 Work Journal Register.*
