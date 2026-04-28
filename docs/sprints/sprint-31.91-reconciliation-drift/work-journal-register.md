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
| **Refreshed at** | 2026-04-28, end-of-Session-5a.2 verdict |
| **Anchor commit** | `d24c413` (S5a.2 Tier 2 review CLEAR) + `9475d91` (impl); CI green |
| **Sessions complete** | 0, 1a, 1b, 1c, 2a, 2b.1, 2b.2, 2c.1, 2c.2 (+ impromptu DEF-216 hotfix), 2d, 3, 4 (+ in-sprint S4 integration-marker hotfix), 5a.1, 5a.2 |
| **Tier 3 reviews complete** | #1 (PROCEED) |
| **Active session** | None — between sessions; cleared to proceed to Session 5b |
| **Sprint phase** | All 4 architectural tracks complete. **Track D Sessions 1 + 2 of 6 complete** (alert observability foundation in place + persistence + auto-resolution policy + WS fan-out + migration framework). Sprint moves to S5b (auto-resolution policy completion + IBKR emitter TODOs + E2E + Alpaca behavioral check) → Tier 3 #2 → S5c/d/e → sprint close-out |
| **Workflow protocol version** | 1.2.0 (per-session register discipline formalized) |

---

## Sprint Identity (Pinned)

- **Sprint:** `sprint-31.91-reconciliation-drift`
- **Predecessor:** Sprint 31.9 (sealed 2026-04-24)
- **Mode:** HITL on `main`
- **Primary defects:** DEF-204 (reconciliation drift / phantom-short — all architectural layers LIVE + falsifiable validation gate LIVE), DEF-014 (alert observability gap — RESOLVES at S5e)
- **Operational mitigation:** Operator runs `scripts/ibkr_close_all_positions.py` daily — REQUIRED, NOT OPTIONAL. Cessation criteria #1 + #2 + #3 SATISFIED post-S4; #4 + #5 still pending
- **Reserved DECs at planning:** DEC-385 (MATERIALIZED at S2d), DEC-386 (MATERIALIZED at Tier 3 #1), DEC-387 (FREED), DEC-388 (alert observability architecture, MATERIALIZES at S5e)

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
| **After S5a.2** | **5,222 (+20)** | **5,261** | **866** | **+142** |

**Sprint cumulative delta:** +142 pytest (operator-local frame), 0 Vitest.

**Bookkeeping discipline note:** S5a.2 closeout cited `tests_added: 20` matching actual delta (vs S5a.1's +21 claim vs +18 actual — RULE-038 sub-bullet feedback was internalized cleanly).

**Test_main.py baseline drift:** Pre-existing 27 pass / 5 skip / 12 fail (S5a.2 verified zero session-2d delta on this file via `git stash` + re-run; reviewer independently verified via `git checkout 5f6b2a6 && pytest tests/test_main.py -q`). Same DEF-048 family of pre-existing failures across all sessions.

**ADMINISTRATIVE NOTE:** CLAUDE.md test count baseline still cites `5,080`; actual operator-local now 5,222. Sprint-end doc-sync MUST refresh.

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
| DEC-388 | Alert observability architecture (resolves DEF-014). **Foundation in place at S5a.1; persistence + auto-resolution + WS + migration framework added at S5a.2** | 5a.1+5a.2+5b+5c+5d+5e | Session 5e close-out |

### Freed

| DEC | Reason |
|---|---|
| DEC-387 | Reserved during planning but not consumed; freed at Tier 3 #1 close |

---

## DEFs

### Filed during Sprint 31.91

| DEF | Source | Description | Disposition | Routed to |
|---|---|---|---|---|
| **DEF-209** (extended) | Tier 3 #1 + S4 verification | `Position.side` AND `ManagedPosition.redundant_exit_observed` persistence in historical-record writers | Sprint 35+ horizon | Sprint 35+ |
| **DEF-211** (extended) | Pre-existing + Apr 27 Findings 3+4 | EXTENDED scope: D1+D2+D3 | Sprint 31.93 (sprint-gating) | Sprint 31.93 |
| **DEF-212** | Tier 3 #1 Concern B | `_OCA_TYPE_BRACKET = 1` constant drift risk | Sprint 31.92 | Sprint 31.92 |
| **DEF-213** | Tier 3 #1 Concern C | `SystemAlertEvent.metadata` schema gap. Schema half S2b.1 + atomic-migration half S5a.1. **FULLY RESOLVED** | Mark RESOLVED in CLAUDE.md at sprint-end | RESOLVED |
| **DEF-214** | Apr 27 debrief Finding 1 | EOD verification timing race + side-blind classification. **RESOLVED at S5a.1** | Mark RESOLVED in CLAUDE.md at sprint-end | RESOLVED |
| **DEF-215** | Apr 27 debrief Finding 2 | Reconciliation per-cycle log spam | DEFERRED with sharp revisit trigger | Deferred |
| **DEF-216** | S2c.2 CI failure | `test_get_regime_summary` ET-midnight rollover race | RESOLVED in impromptu hotfix `c36a30c` | Mark RESOLVED in CLAUDE.md at sprint-end |
| **DEF-208** | S4 spec Phase D Item 1 grep | Live-trading test fixture missing | Filed; routed for future session | Future session |

### Filed pre-Sprint 31.91, status changes

| DEF | Status |
|---|---|
| DEF-204 | All architectural layers LIVE post-S3 + falsifiable validation gate LIVE post-S4. Empirical validation pending at first OCA-effective paper session (Apr 28+) |
| DEF-014 | Alert observability gap — **persistence + WS + auto-resolution policy + migration framework now in place** (S5a.1 + S5a.2); FULLY RESOLVES at Session 5e |
| DEF-158 | Flatten retry side-blindness — RESOLVED in S3 (commit `a11c001`). Mark RESOLVED at sprint-end |
| DEF-177 | `RejectionStage` enum missing distinct values for `MARGIN_CIRCUIT` and `phantom_short_gate` — overload `"risk_manager"`; cleanup gated to dedicated cross-domain session |
| DEF-199 | EOD Pass 2 A1 fix preserved — UNCHANGED across S0–S5a.2 |

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
| **DEC-385 materialization** | S2d | Side-aware reconciliation contract complete across 6 sessions |
| B22 runbook for `live-operations.md` | S2d | 7 subsections landed in-sprint |
| Architecture catalog `**reconciliation**` block | S2d | Added at `docs/architecture.md:1945-1949` |
| **DEF-158 closure** | S3 | 3-branch side-aware gate at `_check_flatten_pending_timeouts:3276-3341` |
| `phantom_short_retry_blocked` alert taxonomy | S3 | New CRITICAL alert type for DEF-158 retry path |
| OCA-EXEMPT comment refresh for `_check_flatten_pending_timeouts` | S3 | `# OCA-EXEMPT:` regression-guard marker preserved |
| HIGH #4 decomposed live-enable gate | S4 | 3 gates per HIGH #4 in `pre-live-transition-checklist.md` Part 5a |
| Mass-balance assertion at session debrief (Sprint Invariant 17) | S4 | Script + 7 synthetic tests + run against real Apr 24 log |
| Spike script freshness (Sprint Invariant 22) | S4 | Parser + ISO-with-dashes |
| Phase 7.4 slippage watch | S4 | Inserted into `market-session-debrief.md` |
| B28 spike trigger registry | S4 | `live-operations.md` restructured |
| Item 7 three-source filename standardization | S4 | All 3 load-bearing surfaces use ISO-with-dashes |
| Item 1 (debrief_export consumer grep) | S4 | Verified zero current consumers; A6 NOT triggered |
| Item 4 (mass-balance precedence) | S4 | Implemented |
| **DEF-204 falsifiable validation gate** | S4 | IMSR replay + mass-balance script with RULE-051 anchors |
| **DEF-213 atomic-migration half** | S5a.1 | 2 pre-existing emitters migrated. **DEF-213 FULLY RESOLVED** |
| **DEF-214** | S5a.1 | Requirement 0.5 — EOD flatten verification fixed |
| **HealthMonitor consumer subscription wiring** | S5a.1 | `SystemAlertEvent` handler + `event_bus.subscribe()` |
| **`AlertsConfig` Pydantic model + YAML stanza** | S5a.1 | New model in both `system.yaml` + `system_live.yaml` |
| **Alerts REST routes** | S5a.1 | New `argus/api/routes/alerts.py` (~360 LOC); 3 endpoints JWT-gated |
| **`alert_acknowledgment_audit` SQLite table** | S5a.1 | New table in `data/operations.db`; idempotent DDL |
| **5 EOD emission paths distinct** | S5a.1 | Side-aware classification with 3 distinct emission paths |
| **All 11 emitter sites populate `metadata`** (DEF-213 atomic-migration scope COMPLETE) | S5a.1 | Now 13 sites total post-S5a.1 |
| Architecture catalog `**alerts**` block | S5a.1 | Added; freshness gate now passes |
| **F2 (S5a.1) — `get_archived_alert_by_id` O(N) linear scan** | S5a.2 | Replaced with SQLite-indexed query |
| **F3 (S5a.1) — In-memory state loss on restart** | S5a.2 | `alert_state` table + `rehydrate_alerts_from_db()` |
| **F4 (S5a.1) — Fire-and-forget event dispatch may lose alerts on shutdown-mid-publish** | S5a.2 | Persistence-on-consume pattern: `_persist_alert` writes BEFORE in-memory mutation |
| **`auto_resolved` test scaffolding** (S5a.1 carry-forward) | S5a.2 | No longer needed — real predicates fire ARCHIVED state via `_auto_resolve` |
| **`prior_engagement_source` becomes lookup post-S5a.1** | S5a.2 (partial) | Threshold provider injection pattern; full alignment with persisted IDs may extend to S5b |
| **S5a.2 should persist alerts BEFORE mutating `_active_alerts`** | S5a.2 | Persistence-on-consume verified in Test #3 |
| **S5a.2 replace `get_archived_alert_by_id` linear scan with SQLite-indexed query** | S5a.2 | SQLite `alert_state` queries |
| **S5a.2 emit-time persistence design consideration** | S5a.2 | Architecture decision: persistence-on-consume in HealthMonitor (not at emitter) — preserves emitter contract decoupling |
| **S5a.2 audit-log retention periodic prune** | S5a.2 | `_retention_loop` + VACUUM via `asyncio.to_thread` |
| **S5a.2 `system_alerts` table schema migration plan** | S5a.2 | Migration framework + Migration v1 in `argus/data/migrations/operations.py` |
| **WebSocket fan-out (`/ws/v1/alerts`)** | S5a.2 | New `argus/api/websocket/alerts_ws.py`; 4 message types; JWT auth via first message |
| **Auto-resolution policy table for all 8 alert types** | S5a.2 | `argus/core/alert_auto_resolution.py` with 8 predicates + `NEVER_AUTO_RESOLVE` sentinel |
| **`phantom_short` predicate single-source-of-truth coupling with S2c.2 threshold** | S5a.2 | `threshold_provider` injection; no duplicated AlertsConfig field; verified by static-source check + behavioral test |
| **Migration framework for `data/operations.db`** | S5a.2 | First time in ARGUS — `argus/data/migrations/{__init__,framework,operations}.py` with `Migration` dataclass + `apply_migrations()` + `current_version()` |
| **`schema_version` table** | S5a.2 | Migration framework version tracking |
| **Architecture catalog WebSocket table updated** | S5a.2 | Catalog freshness gate passes |

---

## Outstanding Code-Level Items (Sprint-Tracked, Not DEF-Worthy)

| Item | Severity | Source | Notes |
|---|---|---|---|
| `asyncio.get_event_loop().time()` in IBKR polling loop | LOW | S0 | Cleanup deferred until Python floor bumps to 3.12+ |
| DISCOVERY line-number anchors drifted >5 lines from spec for `place_bracket_order` and rollback path | LOW | S1a | C6 soft halt |
| Generic Error 201 logged at WARNING | LOW (accepted) | S1a | Pre-Sprint-31.91 baseline was WARNING |
| Simultaneous-multiple-positions-same-symbol OCA edge case | OBSERVATIONAL | S1a | Naturally handled |
| Latent rollback-flag inconsistency under `bracket_oca_type=0` | INFORMATIONAL | S1b JC2 | Bounded by RESTART-REQUIRED note |
| Revision-rejected fresh T1/T2 resubmissions outside original bracket OCA group | LOW (cleanup-eligible) | S1b Follow-Up #4 | Bracket OCA covers normal operation |
| Failure-mode docs for `live-operations.md` "Phantom-Short Gate Diagnosis and Clearance" | RESOLVED in S2d (B22) | S1c | Sprint-end doc-sync verify presence |
| B5-MILD line shift — call site `:1505-1535` spec → `:1519-1553` post-edit | LOW (acceptable) | S2a | No spec adjustment needed |
| EventBus dispatch async-via-`asyncio.create_task`; tests need `_reconcile_and_drain` helper | OBSERVATIONAL | S2b.1 | Pattern matches |
| Cycle 1-2 WARNING is unthrottled but bounded | LOW (acceptable) | S2b.1 | ThrottledLogger compliance reviewed |
| Pass 1 retry SELL detection at `:1777` consistency gap | LOW (consistency gap) | S2b.2 Edge Case 3 | Future session |
| `HealthMonitor.set_order_manager()` production wiring at startup deferred — NOT addressed in S5a.2 (no cross-component access needed for auto-resolution) | RULE-007 deferral | S2b.2 Edge Case 1 | Future or S5b if needed |
| Spec do-not-modify line range `:1670-1750` for `order_manager.py` does NOT actually contain SELL-detection branching | LOW (spec-anchor discrepancy) | S2b.2 RULE-038 #3 + S3 B5-informational | Future impl prompts |
| `logger.info` breakdown lines on margin reset site previously absent | INFORMATIONAL | S2b.2 Edge Case 4 | No existing log-line assertion picks them up |
| Persistence failure leaves disk state stale until restart re-detection | LOW (documented contract) | S2c.1 review concern #1 | DEC-345 fire-and-forget; 60s reconciliation cycle bounds recovery |
| `OrderManager.stop()` does not await `_pending_gate_persist_tasks` | LOW (same-family follow-on) | S2c.1 review concern #2 | NOT addressed in S2d/S3/S4/S5a.1/S5a.2; eligible for future improvement |
| `rejection_stage="risk_manager"` overload for `phantom_short_gate` | LOW (DEF-177 covers split) | S2c.1 judgment call #4 + review concern #3 | When DEF-177 cross-domain enum work lands |
| `_phantom_short_clear_cycles` not cleared in `reset_daily_state` (asymmetric) | LOW (defensible either way) | S2c.2 J-2 | Future alignment session |
| LONG-shares branch not directly exercised by 4 new auto-clear tests | LOW (small coverage gap) | S2c.2 reviewer soft observation #2 | Future test |
| Test 6 anchors on S2c.1's rehydration log not S2d's lifespan log | LOW (small docstring/anchor mismatch) | S2d reviewer soft observation #1 | Behaviorally correct |
| `prior_engagement_source` hardcoded as `"reconciliation.broker_orphan_branch"` pre-S5a.1 — partially addressed at S5a.2 via threshold provider injection | LOW (documented inline) | S2d reviewer soft observation #3 | S5b may complete alignment with persisted IDs |
| Audit table `phantom_short_override_audit` has no retention policy by design | OBSERVATIONAL (intentional) | S2d reviewer soft observation #4 | Forensic-grade audit log; correct trade-off |
| Defensive `try/except` around `event_bus.publish` at Branch 2 marked `# pragma: no cover - defensive` | OBSERVATIONAL (intentional) | S3 reviewer Notable Item #2 | Idiomatic and safe |
| Test 3 (Branch 3) asserts no `SystemAlertEvent` at all | OBSERVATIONAL (intentional defensive) | S3 reviewer Notable Item #3 | Future regression adding an alert to Branch 3 will require deliberate test update |
| Mass-balance script regex doesn't pick up trail/escalation SELL placements | LOW (conservative-correct flagging) | S4 closeout | Operator confirms by symbol-trace |
| `Position closed` log line lacks share count | LOW (test-side reconstruction) | S4 closeout | Not a runtime-code dependency |
| `Order filled:` log line lacks symbol/side | LOW (test/script-side reconstruction) | S4 closeout | Not a runtime-code dependency |
| Item 7 historical references in HISTORICAL/FROZEN docs preserve compact-YYYYMMDD or Unix-epoch | OBSERVATIONAL (intentional preservation) | S4 reviewer Focus Area 6 minor | Future opportunistic doc-hygiene pass |
| Mass-balance script flags 195 `unaccounted_leak` rows on Apr 24 cascade log | EXPECTED (validation surface) | S4 closeout | Apr 24 IS the known-bad cascade reference |
| CLAUDE.md test count baseline still cites `5,080` | ADMINISTRATIVE | S4 closeout RULE-038 disclosure | Sprint-end doc-sync MUST refresh |
| Closeout `tests_added: 21` vs actual +18 (S5a.1) | COSMETIC | S5a.1 reviewer F1 | RULE-038 sub-bullet feedback internalized at S5a.2 (claim matches actual) |
| EOD verify polling residual_shorts last-snapshot semantics could merit inline comment | COSMETIC | S5a.1 reviewer F7 | Optional doc-hygiene |
| Alerts REST routes have no rate limiting (JWT-only) | ACCEPTABLE | S5a.1 reviewer F8 | Per-route throttle if alert volume escalates |
| **NEW (S5a.2):** Predicate-handler subscriptions wired before rehydration completes (no realistic race today; will become real when producers land) | INFORMATIONAL (no realistic race today) | S5a.2 reviewer F1 | When producers for `ReconciliationCompletedEvent`/`IBKRReconnectedEvent`/`DatabentoHeartbeatEvent` land, defer `_subscribe_predicate_handlers()` to AFTER rehydration |
| **NEW (S5a.2):** Duplicate `_AUDIT_DDL` in `argus/api/routes/alerts.py` (S5a.1 leftover) | LOW (cleanup) | S5a.2 reviewer F2 | Migration framework is canonical home; remove from routes file |
| **NEW (S5a.2):** Best-effort SQLite write with WARNING-only log on failure for alert persistence | LOW (consistent with DEC-345 fire-and-forget) | S5a.2 reviewer F3 | Aligned with `EvaluationEventStore` pattern |
| **NEW (S5a.2):** `_evaluate_predicates` broad exception catch on predicate body | DEFENSIVE (reasonable) | S5a.2 reviewer F4 | Production code defensively catching one bad predicate is reasonable |
| **NEW (S5a.2):** `routes/alerts.py` post-commit persistence path swallows exceptions in defensive try | DEFENSIVE (reasonable) | S5a.2 reviewer F5 | Inner already catches; outer is defense-in-depth |
| **NEW (S5a.2):** New event dataclasses are deferred-emission (acknowledged) | DOCUMENTED | S5a.2 reviewer F6 | When producers land, deferred-emission docstring should be updated |

---

## Carry-Forward Watchlist (Active)

| Item | Status | Lands in |
|---|---|---|
| **Daily-flatten cessation** | Conservative criteria #1 + #2 + #3 SATISFIED post-S4; criteria #4 + #5 pending | Sprint-end + 5 paper-session-clean window |
| Operator daily-flatten | REQUIRED, NOT OPTIONAL | Active until criterion #5 |
| `auto_resolved` test scaffolding (S5a.1 test 8) | RESOLVED at S5a.2 | (Done) |
| Banner mount on `Dashboard.tsx` (5c) | Watch | 5e (relocate to `Layout.tsx`) |
| Toast mount on `Dashboard.tsx` (5d) | Watch | 5e (relocate to `Layout.tsx`) |
| `/api/v1/alerts/{id}/audit` endpoint surface | Watch — S5a.1 acknowledgment endpoint logs audit_kind; S5a.2 added `auto_resolution` audit_kind. Verify whether separate `/audit` endpoint still needed | 5e (consume) |
| AlpacaBroker `_check_connected` AttributeError | DISCLOSED | Sprint 31.94 |
| `BracketOrderResult.oca_group_id` exposure | OBSERVATIONAL | Future |
| Tier 3 #1 Concern A (helper relocation) | Implicit DEF-212 sibling | Sprint 31.92 |
| Tier 3 #1 Concerns E + F (test-hygiene) | Backlog | Future |
| **First OCA-effective paper session debrief** | Watch (Apr 28+) | First post-`bf7b869` paper session |
| **First post-S4 paper-session mass-balance run** | Watch | Operator runs `validate_session_oca_mass_balance.py` against first post-`da325a0` session log |
| `HealthMonitor.set_order_manager()` production wiring at startup | NOT addressed in S5a.1 or S5a.2 (no cross-component access needed for auto-resolution policy) | Future or S5b if needed |
| Spec do-not-modify anchor for `order_manager.py` should reference structural rather than line-number anchors | TRACKED | Future impl prompts |
| `OrderManager.stop()` graceful-shutdown await of `_pending_gate_persist_tasks` | Watch | NOT addressed in S2d/S3/S4/S5a.1/S5a.2; eligible for future improvement |
| `_phantom_short_clear_cycles` reset_daily_state symmetry | Watch | Future alignment session |
| LONG-shares-clearing test coverage gap (S2c.2) | Watch | Future session |
| `prior_engagement_source` becomes lookup post-S5a.1 — partially addressed at S5a.2 via threshold provider | Watch | S5b may complete |
| S2d-specific test for lifespan-layer startup log | LOW priority | Future test-hygiene session |
| Two pre-existing operator stashes (`stash@{0}`, `stash@{1}`) | OPERATOR ACTION | At operator's convenience |
| Original Pass 1 retry SELL consistency gap at `:1777` | OBSERVATIONAL | Future session |
| Mass-balance script regex extension for trail/escalation paths | LOW priority | Future session |
| Item 7 historical doc references in frozen artifacts | OBSERVATIONAL | Opportunistic doc-hygiene pass |
| **CLAUDE.md test count baseline refresh** (currently `5,080`; actual operator-local 5,222) | ADMINISTRATIVE | Sprint-end doc-sync |
| **NEW (S5a.2):** Predicate-handler subscriptions wired before rehydration — defer to AFTER rehydration when producers land | DESIGN | Future sprint when producers land |
| **NEW (S5a.2):** Duplicate `_AUDIT_DDL` in `argus/api/routes/alerts.py` cleanup | LOW (cleanup) | Future cleanup |
| **NEW (S5a.2):** `ReconciliationCompletedEvent` producer wiring | DEFERRED | post-31.9 component-ownership sprint or `phantom_short` retry-blocked detection path |
| **NEW (S5a.2):** `IBKRReconnectedEvent` producer wiring | DEFERRED | `post-31.9-reconnect-recovery` sprint (DEF-194/195/196) |
| **NEW (S5a.2):** `DatabentoHeartbeatEvent` producer wiring | DEFERRED | Data-layer health poller (existing `DataResumedEvent` is fallback) |
| **NEW (S5a.2):** Migration framework adoption for other separate DBs (catalyst.db, evaluation.db, regime_history.db, learning.db, vix_landscape.db, counterfactual.db, experiments.db) | OPPORTUNISTIC | Future sprints when those DBs need schema changes |
| **NEW (S5a.2):** Doc-sync sweep check that no production sprint commit lands without updating deferred-emission docstring | LOW priority | Future tooling |
| **NEW (S5a.2):** `tests/api/test_alerts.py` (12) + `tests/api/test_alerts_5a2.py` (20) — kickoff brief's "32 tests" was conflated | COSMETIC | Future kickoff briefs disambiguate |
| **NEW (S5a.2):** S5b — full auto-resolution policy + IBKR emitter TODOs + E2E + Alpaca behavioral check | PLANNED | S5b |
| **NEW (S5a.2):** S5b — wire `acknowledgment_required_severities` gate (consumer of `AlertsConfig` field) | DESIGN | S5b |
| **NEW (S5a.2):** S5b — compose policy with `eod_residual_shorts` (warning) + `eod_flatten_failed` (critical) emitter pair | DESIGN | S5b |
| **NEW (S5a.2):** S5c-5e frontend routes on `metadata.category` structurally + display original acknowledger info on late-ack | DESIGN | S5c-5e |

---

## Pre-Applied Operator Decisions (Re-stated for self-containment)

| # | Decision | Lands In |
|---|---|---|
| Phase D Item 2 | EOD Pass 2 cancel-timeout failure-mode docs + test 7 | Session 1c (RESOLVED) |
| Phase D Item 3 | Health + broker-orphan double-fire dedup → Option C hybrid | Session 2b.2 (RESOLVED) |
| M4 cost-of-error asymmetry | Auto-clear threshold default = 5 | Session 2c.2 (RESOLVED) |
| L3 always-fire-both-alerts | Aggregate at ≥10 + per-symbol always fire | Session 2d (RESOLVED) |
| MEDIUM #13 Alpaca anti-regression | `inspect.getsource` check (not line-number-based) | Session 5b |
| HIGH #1 auto-resolution policy | Explicit per-alert-type predicates (8 alert types covered at S5a.2; 9 alert types total post-S5a.1) | Sessions 5a.2 (RESOLVED) + 5b (full policy completion) |
| HIGH #4 decomposed live-enable gate | 4 criteria (1, 2, 3a, 3b) | Session 4 (RESOLVED) |

---

## Operator Decisions Log (Mid-Sprint)

### 2026-04-27 — Phase D Item 6: Interim Merge Timing → Option C

merge after 1c (already done); KEEP operator daily flatten as belt-and-suspenders.

### 2026-04-27 — Daily-Flatten Cessation Criteria → Conservative

Daily-flatten continues until ALL of:
1. ✅ Session 2d landed and CLEAR (SATISFIED 2026-04-28)
2. ✅ Session 3 landed and CLEAR (SATISFIED 2026-04-28)
3. ✅ Session 4 landed and CLEAR (SATISFIED 2026-04-28)
4. ❌ Sprint 31.91 sealed (pending — needs Track D + doc-sync)
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

### Tier 3 #2 — Pending

- **Anticipated:** After Session 5b lands (combined diff 5a.1+5a.2+5b — alert observability backend)
- **Tier 3 track marker on closeouts:** `alert-observability` (S5a.1 + S5a.2 set this marker)

---

## Emitter-Site Tracking (FINAL — DEF-213 atomic-migration scope COMPLETE)

All 13 alert-emission sites now populate `metadata`:

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

**13 alert-emission sites total.** S5a.2 added no new emitter sites; introduced `auto_resolution` audit_kind dimension only.

**Alert types post-S5a.2 (9 distinct alert_types covered by auto-resolution policy table):**
- `phantom_short` (3 sources; severity `critical`) — auto-resolves on N cycles without re-detection (threshold from S2c.2)
- `phantom_short_retry_blocked` (1 source; severity `critical`) — `NEVER_AUTO_RESOLVE`
- `phantom_short_startup_engaged` (1 source; severity `critical`) — auto-resolves when startup phantoms drained
- per-symbol `phantom_short` from startup rehydration (1 source; severity `critical`) — same as `phantom_short` policy
- `stranded_broker_long` (1 source; severity `warning`) — auto-resolves on reconciliation success
- `eod_residual_shorts` (1 source; severity `warning`) — auto-resolves at next session start
- `eod_flatten_failed` (1 source; severity `critical`) — operator-action-required (likely)
- `cancel_propagation_timeout` (3 invocations) — `NEVER_AUTO_RESOLVE`
- `databento_dead_feed` (1 source; severity TBD) — auto-resolves on `DatabentoHeartbeatEvent` or `DataResumedEvent`

Plus `ibkr_disconnect` + `ibkr_auth_failure` predicates wired for future producers.

---

## SQLite Storage (Sprint 31.91 New Surfaces — UPDATED at S5a.2)

| File | Source session | Schema | Purpose |
|---|---|---|---|
| `data/operations.db` | S2c.1 | `phantom_short_gated_symbols` table (5 cols) | Per-symbol entry-gate state |
| `data/operations.db` | S2d | `phantom_short_override_audit` table (8 cols + 2 indexes) | Forensic audit log of operator overrides |
| `data/operations.db` | S5a.1 | `alert_acknowledgment_audit` table (audit_kinds: `ack`, `duplicate_ack`, `late_ack`) | Forensic audit log of alert acknowledgments |
| **`data/operations.db`** | **S5a.2** | **`alert_state` table + 3 indexes** | Persisted alert state for restart-recovery |
| **`data/operations.db`** | **S5a.2** | **`schema_version` table** | Migration framework version tracking |
| `data/operations.db` | S5a.2 (extension) | `alert_acknowledgment_audit.audit_kind` extended | New `auto_resolution` audit_kind |

**5 tables total in `data/operations.db` post-S5a.2** (`phantom_short_gated_symbols`, `phantom_short_override_audit`, `alert_acknowledgment_audit`, `alert_state`, `schema_version`).

**Migration framework introduced at S5a.2** (first time in ARGUS): `argus/data/migrations/{__init__,framework,operations}.py`. Migration v1 codifies all S5a.1 + S5a.2 tables. Future schema changes register `Migration` objects in per-DB modules.

Sprint-end doc-sync MUST surface all 5 tables in `architecture.md` storage table + `live-operations.md` operational reference.

---

## Validation Infrastructure (Sprint 31.91 New, S4)

| Surface | File | Purpose |
|---|---|---|
| Mass-balance categorized variance script | `scripts/validate_session_oca_mass_balance.py` (462 LOC) | Consumes `logs/argus_YYYYMMDD.jsonl`. H2 + Item 4 precedence, 120s eventual-consistency window, IMSR known-gap escape |
| IMSR replay integration test | `tests/integration/test_imsr_replay.py` | RULE-051 mechanism-signature anchors. `pytest.fail` on missing log; `@pytest.mark.integration` excludes from CI's `-m "not integration"` filter |
| Synthetic-fixture mass-balance tests | `tests/scripts/test_validate_session_oca_mass_balance.py` (7 tests) | Coverage of all H2 and Item 4 categorization rules |
| Spike-filename verification tests | `tests/scripts/test_spike_script_filename.py` (2 tests) | Item 7 surgical-fix verification |

---

## Session Order (Sequential — Strict)

1. ✅ Session 0 (cancel_all_orders API) — CLEAR, commit `9b7246c`
2. ✅ Session 1a (bracket OCA + Error 201 defensive) — CLEAR, commit `b25b419`
3. ✅ Session 1b (standalone-SELL OCA + Error 201 graceful) — CLEAR, commit `6009397`
4. ✅ Session 1c (broker-only paths + reconstruct docstring) — CLEAR, commit `49beae2`
5. ✅ **Tier 3 #1** — PROCEED, verdict commit `df48e31`. **DEC-386 materialized.**
6. ✅ Session 2a (typed reconciliation contract) — CLEAR, commit `813fc3c`
7. ✅ Session 2b.1 (broker-orphan branch + `phantom_short` alert + cycle infrastructure) — CLEAR, commit `4119608`
8. ✅ Session 2b.2 (4 count-filter sites + 1 alert-alignment site + Option C cross-reference) — CLEAR, commit `a6846c6`
9. ✅ Session 2c.1 (per-symbol entry gate + handler + SQLite + M5 rehydration ordering) — CLEAR, commit `0c034b3`
10. ✅ Session 2c.2 (clear-threshold + auto-clear, default 5) — CLEAR, commit `24320e5`
11. ✅ Impromptu hotfix DEF-216 — CLEAR, commit `c36a30c`
12. ✅ Session 2d (operator override API + audit-log + L3 always-both startup alerts + L15 configurable threshold + B22 runbook) — CLEAR, commit `93f56cd`. **DEC-385 materialized; Track B COMPLETE.**
13. ✅ Session 3 (DEF-158 retry side-check + severity fix + `phantom_short_retry_blocked` alert taxonomy) — CLEAR, commit `a11c001`. **DEF-158 RESOLVED; Track C COMPLETE.**
14. ✅ Session 4 (mass-balance categorized + IMSR replay + decomposed live-enable gate + Phase 7.4 slippage + B28 spike registry + Item 7 standardization) — CLEAR, barrier `da325a0`. **DEF-204 falsifiably validated; validation-infrastructure layer COMPLETE.**
15. ✅ Session 5a.1 (HealthMonitor consumer + `AlertsConfig` + REST + acknowledgment + DEF-213 atomic-migration + DEF-214) — CLEAR, commit `0236e27`. **DEF-213 + DEF-214 RESOLVED; Track D foundation in place.**
16. ✅ **Session 5a.2** (WS fan-out + SQLite persistence + auto-resolution policy + retention + migration framework) — CLEAR, commit `9475d91`. **3 S5a.1 carry-forwards (F2/F3/F4) RESOLVED; persistence + auto-resolution + WS + migration framework all live.**
17. ⏳ **Session 5b** (full auto-resolution policy completion + IBKR emitter TODOs + E2E + Alpaca behavioral check) ← NEXT
18. **Tier 3 #2** — combined diff 5a.1+5a.2+5b
19. Session 5c (useAlerts hook + Dashboard banner)
20. Session 5d (toast notification + acknowledgment UI flow)
21. Session 5e (Observatory alerts panel + cross-page integration). **DEC-388 materializes.**
22. Sprint close-out + doc-sync handoff. **DEC-385, DEC-386, DEC-388 written to `decision-log.md`.**

---

## Sprint-End Deliverable (Forward-Looking)

When Session 5e clears, the Work Journal produces the doc-sync handoff per `templates/work-journal-closeout.md` + `templates/doc-sync-automation-prompt.md`.

**Items the sprint-end doc-sync MUST surface:**
- DEC-386 documentation (already done in Tier 3 #1 doc-sync; verify)
- DEC-385 documentation (MATERIALIZED at S2d; needs writing)
- DEC-388 documentation (materializing at Session 5e)
- All 8 DEFs filed in this sprint integrated into CLAUDE.md (DEF-208/209/211/212/213/214/215/216)
- DEF-213 marked FULLY RESOLVED (schema half S2b.1 + atomic-migration half S5a.1)
- DEF-214 marked RESOLVED via S5a.1
- DEF-216 marked RESOLVED via impromptu hotfix `c36a30c`
- DEF-158 marked RESOLVED via S3 (commit `a11c001`)
- RSK-DEC-386-DOCSTRING in `risk-register.md`
- CLAUDE.md test count baseline refresh
- Architecture.md OCA architecture (already done; verify) + side-aware reconciliation contract per DEC-385 (new) + retry-path side-check section (new, S3) + validation infrastructure layer (S4) + alert observability per DEC-388 (S5a.1+S5a.2+S5b+S5c+S5d+S5e)
- Architecture.md storage table: add all 5 `data/operations.db` tables (S2c.1 + S2d + S5a.1 + S5a.2 ×2)
- Architecture catalog `**reconciliation**` block (already done in S2d; verify)
- Architecture catalog `**alerts**` block (already done in S5a.1; verify)
- Architecture catalog `**WS /ws/v1/alerts**` block (already done in S5a.2; verify)
- `live-operations.md` updates: extensive list per S2d/S3/S4/S5a.1/S5a.2 carry-forwards
- `pre-live-transition-checklist.md` (already done in S4 Part 5a; verify)
- `protocols/market-session-debrief.md` Phase 7.4 slippage watch (already done in S4; verify)
- Apr 27 debrief findings folded (already done; verify)
- Sprint-history.md entry for Sprint 31.91 (covers S0–S5e + 1 Tier 3 + 1 impromptu + 1 in-sprint hotfix)
- Migration framework adoption note (S5a.2 introduced first migration framework in ARGUS)
- DEF-204 falsifiable validation gate operational reference (S4)
- 3 deferred-emission events documented (`ReconciliationCompletedEvent`, `IBKRReconnectedEvent`, `DatabentoHeartbeatEvent`) — predicates wired today; producers in future sprints

---

*End Sprint 31.91 Work Journal Register.*
