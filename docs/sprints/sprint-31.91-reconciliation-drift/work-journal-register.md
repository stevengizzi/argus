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
| **Refreshed at** | 2026-04-28, end-of-Session-2d verdict |
| **Anchor commit** | `aea3858` (S2d Tier 2 review CLEAR + impl `93f56cd`); CI run `25034590254` GREEN |
| **Sessions complete** | 0, 1a, 1b, 1c, 2a, 2b.1, 2b.2, 2c.1, 2c.2 (+ impromptu DEF-216 hotfix), 2d |
| **Tier 3 reviews complete** | #1 (PROCEED) |
| **Active session** | None — between sessions; cleared to proceed to Session 3 |
| **Sprint phase** | Track A complete (OCA architecture, DEC-386 materialized at Tier 3 #1); **Track B COMPLETE (side-aware reconciliation, DEC-385 materializes at S2d)**; Sessions 3 (DEF-158 retry side-check) + 4 (mass-balance + IMSR replay) pending; Track D (alert observability, 6 sessions + Tier 3 #2 + DEC-388) pending |
| **Workflow protocol version** | 1.2.0 (per-session register discipline formalized) |

---

## Sprint Identity (Pinned)

- **Sprint:** `sprint-31.91-reconciliation-drift`
- **Predecessor:** Sprint 31.9 (sealed 2026-04-24)
- **Mode:** HITL on `main`
- **Primary defects:** DEF-204 (reconciliation drift / phantom-short mechanism — **DEC-385 contract NOW LIVE**), DEF-014 (alert observability gap)
- **Operational mitigation:** Operator runs `scripts/ibkr_close_all_positions.py` daily — REQUIRED, NOT OPTIONAL per Apr 27 evidence. **Conservative cessation criterion #1 SATISFIED post-S2d**; criteria #2-#5 still pending.
- **Reserved DECs at planning:** DEC-385 (side-aware reconciliation contract — **MATERIALIZED at S2d**), DEC-386 (OCA-group threading + broker-only safety — MATERIALIZED at Tier 3 #1), DEC-387 (reserved but not consumed — freed), DEC-388 (alert observability architecture, resolves DEF-014 — Sessions 5a.1/5a.2/5b/5c/5d/5e)

---

## Test Tally

| Session | pytest (main) | pytest total (incl. test_main.py) | Vitest | Cumulative new tests |
|---|---|---|---|---|
| **Sprint baseline** | 5,080 | 5,124 | 866 | — |
| After S0 | 5,088 (+8) | 5,132 | 866 | +8 |
| After S1a | 5,106 (+18) | 5,150 | 866 | +26 |
| After S1b | 5,121 (+15) | 5,165 | 866 | +41 |
| After S1c | 5,128 (+7) | 5,167 | 866 | +48 |
| After Tier 3 #1 doc-sync | 5,128 (+0, doc-only) | 5,167 | 866 | +48 |
| After S2a | 5,133 (+5) | 5,172 | 866 | +53 |
| After S2b.1 | 5,139 (+6) | 5,178 | 866 | +59 |
| After S2b.2 | 5,153 (+14) | 5,192 | 866 | +73 |
| After S2c.1 | 5,159 (+6) | 5,198 | 866 | +79 |
| After S2c.2 | 5,163 (+4) | 5,202 | 866 | +83 |
| After DEF-216 hotfix | 5,163 (+0; fix to existing test) | 5,202 | 866 | +83 |
| **After S2d** | **5,169 (+6)** | **5,208** | **866** | **+89** |

**Sprint cumulative delta:** +89 pytest, 0 Vitest.

**Test_main.py baseline:** Pre-existing baseline drift (31 pass / 5 skip / 8 fail) noted at S2d; reviewer verified zero S2d-introduced delta on this file. The pre-existing failures are documented in CLAUDE.md DEF-048 lineage and are NOT regressions from any Sprint 31.91 session. Original sprint-baseline assumption was 39 pass + 5 skip; actual current state is 31 pass / 5 skip / 8 fail. This is a register tracking-correction, not a Sprint 31.91 issue.

---

## DECs

### Materialized

| DEC | Description | Sessions | Status |
|---|---|---|---|
| **DEC-386** | OCA-Group Threading + Broker-Only Safety (4-layer architecture: API contract → bracket OCA → standalone-SELL OCA → broker-only safety) | 0+1a+1b+1c | **Written** to `docs/decision-log.md` post-Tier-3-#1 |
| **DEC-385** | Side-Aware Reconciliation Contract (6-layer architecture: typed dataclass foundation → broker-orphan branch detection → count-filter alignment + Health hybrid → entry gate engagement + SQLite persistence + M5 rehydration → 5-cycle auto-clear → operator override + audit-log + L3 always-both startup alerts + L15 configurable threshold + B22 runbook) | 2a+2b.1+2b.2+2c.1+2c.2+2d | **MATERIALIZED at Session 2d**; will be written to `docs/decision-log.md` at sprint-end doc-sync. Latest-DEC pointer will advance from DEC-386 → DEC-388 (skipping DEC-387 which was freed) once DEC-388 also materializes at S5e |

### Reserved (not yet materialized)

| DEC | Description | Sessions | Materializes at |
|---|---|---|---|
| DEC-388 | Alert observability architecture (resolves DEF-014) | 5a.1/5a.2/5b/5c/5d/5e | Session 5e close-out |

### Freed

| DEC | Reason |
|---|---|
| DEC-387 | Reserved during planning but not consumed; freed at Tier 3 #1 close |

---

## DEFs

### Filed during Sprint 31.91

| DEF | Source | Description | Disposition | Routed to |
|---|---|---|---|---|
| **DEF-209** (extended) | Tier 3 #1 Concern D | `Position.side` AND `ManagedPosition.redundant_exit_observed` persistence in historical-record writers | Sprint 35+ horizon | Sprint 35+ |
| **DEF-211** (extended) | Pre-existing + Apr 27 Findings 3+4 | EXTENDED scope: D1+D2+D3 | Sprint 31.93 (sprint-gating) | Sprint 31.93 |
| **DEF-212** | Tier 3 #1 Concern B | `_OCA_TYPE_BRACKET = 1` constant drift risk | Sprint 31.92 | Sprint 31.92 |
| **DEF-213** | Tier 3 #1 Concern C | `SystemAlertEvent.metadata` schema gap. **PARTIAL-RESOLVED in S2b.1** (schema half); atomic emitter migration of 2 pre-existing emitters remains S5a.1 scope per Pre-Flight Check 7's "skip Requirement 0" branch | **Sprint 31.91 Session 5a.1 sprint-gating** (atomic-migration half only) | Sprint 31.91 Session 5a.1 |
| **DEF-214** | Apr 27 debrief Finding 1 | EOD verification timing race + side-blind classification | **Sprint 31.91 Session 5a.1 sprint-gating** — Requirement 0.5 | Sprint 31.91 Session 5a.1 |
| **DEF-215** | Apr 27 debrief Finding 2 | Reconciliation per-cycle log spam | DEFERRED with sharp revisit trigger | Deferred |
| **DEF-216** | S2c.2 CI failure on `1a14258` | `tests/core/test_regime_history.py::test_get_regime_summary` ET-midnight rollover race | **RESOLVED in impromptu hotfix `c36a30c`** | Mark RESOLVED in CLAUDE.md at sprint-end doc-sync |

### Filed pre-Sprint 31.91, status unchanged

| DEF | Status |
|---|---|
| DEF-204 | Reconciliation drift / phantom-short mechanism — **ALL 6 LAYERS LIVE post-S2d**: detection (S2b.1) + count-filter (S2b.2) + entry-gate (S2c.1) + auto-clear (S2c.2) + manual override + audit-log (S2d). DEC-385 contract complete. Falsifiable validation pending at first OCA-effective paper session (Apr 28+). Pending Sprint 31.91 work: DEF-158 retry side-check (S3) + mass-balance assertion (S4) |
| DEF-014 | Alert observability gap — RESOLVES at Session 5e |
| DEF-158 | Flatten retry side-blindness — RESOLVES in Session 3 (NEXT) |
| DEF-177 | `RejectionStage` enum missing distinct values for `MARGIN_CIRCUIT` and `phantom_short_gate` — S2c.1 + S2c.2 overload `"risk_manager"`; cleanup gated to dedicated cross-domain session |
| DEF-199 | EOD Pass 2 A1 fix preserved — UNCHANGED across S0–S2d |

### Anticipated but NOT filed

| Anticipated DEF | Reason not filed |
|---|---|
| DEF-208 | No fresh evidence requiring filing through S2d |
| DEF-210 | Same — original anticipated routing not opened by any session in flight |

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
| `Order.oca_group_id` field arrival | S1a | LANDED via `Order.ocaGroup` + `Order.ocaType` |
| `ManagedPosition.oca_group_id` persistence | S1a | LANDED |
| Defensive Error 201 on T1/T2 submission preserving DEC-117 | S1a | LANDED — `_is_oca_already_filled_error()` |
| Caller-side ERROR log suppression on OCA-filled | S1b | RESOLVED — `_handle_oca_already_filled` helper |
| Phase D Item 2 (EOD Pass 2 cancel-timeout failure-mode docs + test 7) | S1c | RESOLVED |
| Broker-only path routing through `cancel_all_orders(symbol, await_propagation=True)` | S1c | RESOLVED — 3 paths gated |
| `reconstruct_from_broker` docstring update | S1c | RESOLVED |
| `_OCA_TYPE_BRACKET` doc-sync paragraph for `live-operations.md` | Tier 3 #1 doc-sync | LANDED via `df48e31` |
| Per-session register discipline formalized in workflow metarepo | S2a | LANDED — workflow v1.2.0 |
| **DEF-213 schema-extension half** | S2b.1 (PARTIAL — atomic emitter migration still S5a.1) | `SystemAlertEvent.metadata` field added |
| **2b.2 cross-component coupling on `_broker_orphan_last_alerted_cycle`** | S2b.2 (read implementation complete; production wiring deferred S5a.1+) | `HealthMonitor._order_manager` reads dict via `getattr` defensive pattern |
| **Spec invariant 8 wrong attribution** | S2b.2 | Disclosed and reconciled per RULE-038 |
| **DEF-216** ET-midnight rollover flake | Impromptu hotfix `c36a30c` | Anchor all snapshot timestamps + query date to noon ET |
| **Phase D pre-applied operator decision L3 (always-fire-both-alerts)** | S2d | Aggregate at ≥10 + per-symbol always fire (no suppression). Tests 4 and 5 lock the behavior |
| **DEC-385 materialization** | S2d | Side-aware reconciliation contract complete across 6 sessions; will be written to `decision-log.md` at sprint-end |
| **B22 runbook for `live-operations.md` "Phantom-Short Gate Diagnosis and Clearance"** | S2d | 7 subsections landed in-sprint at `docs/live-operations.md:680-769` |
| **Architecture catalog `**reconciliation**` block (S4 REST endpoint catalog)** | S2d | Added at `docs/architecture.md:1945-1949` |

---

## Outstanding Code-Level Items (Sprint-Tracked, Not DEF-Worthy)

| Item | Severity | Source | Notes |
|---|---|---|---|
| `asyncio.get_event_loop().time()` in IBKR polling loop | LOW | S0 | Cleanup deferred until Python floor bumps to 3.12+ |
| DISCOVERY line-number anchors drifted >5 lines from spec for `place_bracket_order` and rollback path | LOW | S1a | C6 soft halt |
| Generic Error 201 logged at WARNING (not ERROR per impl-prompt) | LOW (accepted) | S1a | Pre-Sprint-31.91 baseline was WARNING |
| Simultaneous-multiple-positions-same-symbol OCA edge case | OBSERVATIONAL | S1a | Naturally handled |
| Latent rollback-flag inconsistency under `bracket_oca_type=0` | INFORMATIONAL | S1b JC2 | Bounded by RESTART-REQUIRED note |
| Revision-rejected fresh T1/T2 resubmissions outside original bracket OCA group | LOW (cleanup-eligible) | S1b Follow-Up #4 | Bracket OCA covers normal operation |
| Failure-mode docs for `live-operations.md` "Phantom-Short Gate Diagnosis and Clearance" | RESOLVED in S2d (B22) | S1c | Sprint-end doc-sync need only verify presence |
| B5-MILD line shift — call site `:1505-1535` spec → `:1519-1553` post-edit | LOW (acceptable) | S2a | No spec adjustment needed |
| EventBus dispatch async-via-`asyncio.create_task`; tests need `_reconcile_and_drain` helper | OBSERVATIONAL | S2b.1 | Pattern matches `test_broker_only_paths_safety.py` |
| Cycle 1-2 WARNING is unthrottled but bounded | LOW (acceptable) | S2b.1 | ThrottledLogger compliance reviewed |
| Pass 1 retry SELL detection at `order_manager.py:1777` is sibling to Pass 2 but NOT alerted with `phantom_short` | LOW (consistency gap) | S2b.2 Edge Case 3 | Future session can extend taxonomy |
| `HealthMonitor.set_order_manager()` production wiring at startup deferred — `main.py` is do-not-modify | RULE-007 deferral | S2b.2 Edge Case 1 | S5a.1+ migration |
| Spec do-not-modify line range `:1670-1750` for `order_manager.py` does NOT actually contain SELL-detection branching | LOW (spec-anchor discrepancy) | S2b.2 RULE-038 #3 | Future impl prompts should reference structural anchor |
| `logger.info` breakdown lines on margin reset site previously absent | INFORMATIONAL | S2b.2 Edge Case 4 | No existing log-line assertion picks them up |
| Persistence failure leaves disk state stale until restart re-detection | LOW (documented contract) | S2c.1 review concern #1 | DEC-345 fire-and-forget; 60s reconciliation cycle bounds recovery |
| `OrderManager.stop()` does not await `_pending_gate_persist_tasks` | LOW (same-family follow-on) | S2c.1 review concern #2 | NOT addressed in S2d; eligible for future graceful-shutdown improvement |
| `rejection_stage="risk_manager"` overload for `phantom_short_gate` | LOW (DEF-177 covers split) | S2c.1 judgment call #4 + review concern #3 | When DEF-177 cross-domain `RejectionStage` enum work lands |
| `_phantom_short_clear_cycles` not cleared in `reset_daily_state` (asymmetric with `_broker_orphan_long_cycles`) | LOW (defensible either way) | S2c.2 J-2 | Eligible for alignment in a future session |
| LONG-shares branch (`broker_pos.side == OrderSide.BUY`) not directly exercised by 4 new auto-clear tests | LOW (small coverage gap) | S2c.2 reviewer soft observation #2 | Future test would lock the LONG path |
| **NEW (S2d):** Test 6 anchors on S2c.1's rehydration log not S2d's lifespan log | LOW (small docstring/anchor mismatch) | S2d reviewer soft observation #1 | Behaviorally correct; future S2d-specific test could lock the lifespan-layer log explicitly |
| **NEW (S2d):** `prior_engagement_source` hardcoded as `"reconciliation.broker_orphan_branch"` pre-S5a.1 | LOW (documented inline) | S2d reviewer soft observation #3 | Becomes lookup post-S5a.1 |
| **NEW (S2d):** Audit table `phantom_short_override_audit` has no retention policy by design (append-only forever per Sprint 31.91 retention spec) | OBSERVATIONAL (intentional) | S2d reviewer soft observation #4 | Forensic-grade audit log; rare events; small row size; correct trade-off |

---

## Carry-Forward Watchlist (Active)

| Item | Status | Lands in |
|---|---|---|
| **Daily-flatten cessation** | Conservative criterion #1 SATISFIED post-S2d (Session 2d landed and CLEAR); criteria #2-#5 pending | Sprint-end + 5 paper-session-clean window |
| Operator daily-flatten (`scripts/ibkr_close_all_positions.py`) | REQUIRED, NOT OPTIONAL | Active until criterion #5 |
| `auto_resolved` test scaffolding (5a.1 test 8) | Watch | 5a.2 (must remove) |
| Banner mount on `Dashboard.tsx` (5c) | Watch | 5e (relocate to `Layout.tsx`) |
| Toast mount on `Dashboard.tsx` (5d) | Watch | 5e (relocate to `Layout.tsx`) |
| `/api/v1/alerts/{id}/audit` endpoint surface | Watch | 5a.1 (verify exists), 5e (consume) |
| AlpacaBroker `_check_connected` AttributeError | DISCLOSED, out-of-scope | Sprint 31.94 |
| `BracketOrderResult.oca_group_id` exposure | OBSERVATIONAL | Future API-cleanliness |
| Tier 3 #1 Concern A (`_is_oca_already_filled_error` helper module abstraction leakage) | Implicit DEF-212 sibling | Sprint 31.92 |
| Tier 3 #1 Concern E (test fixture drift — `MagicMock()` brokers in 12+ files) | Test-hygiene backlog | Future test-hygiene session |
| Tier 3 #1 Concern F (Test 4 `get_positions.side_effect` brittleness) | Test-hygiene backlog | Future test-hygiene session |
| First OCA-effective paper session debrief | Watch | Apr 28 or later (first post-`bf7b869` session) |
| Emitter-site line-number drift in `order_manager.py` | TRACKED | S5a.1 pre-flight grep canonical |
| 6 emitter sites at S2d close (all populate `metadata` from day one — zero S5a.1 migration burden) | TRACKED for S5a.1 grep | S5a.1 |
| Pass 1 retry SELL `phantom_short` alert extension — consistency-gap | Future session | TBD |
| `HealthMonitor.set_order_manager()` production wiring at startup | Watch | S5a.1+ — 5a.1 should invoke alongside consumer subscription wiring |
| Spec do-not-modify anchor for `order_manager.py` should reference structural `elif side == OrderSide.SELL:` rather than line numbers | TRACKED | Future impl prompts |
| `OrderManager.stop()` graceful-shutdown await of `_pending_gate_persist_tasks` | Watch | NOT addressed in S2d; eligible for future improvement |
| `_phantom_short_clear_cycles` reset_daily_state symmetry with `_broker_orphan_long_cycles` | Watch | Future alignment session |
| LONG-shares-clearing test coverage gap (S2c.2) | Watch | Future session |
| `prior_engagement_source` becomes lookup post-S5a.1 | Watch | S5a.1 |
| **NEW (S2d):** S2d-specific test for lifespan-layer startup log (vs S2c.1 rehydration log) | LOW priority | Future test-hygiene session |
| **NEW (S2d, external):** Two pre-existing operator stashes (`stash@{0}` from `8ccac67` audit FIX-21 2026-04-22; `stash@{1}` from `2a59083` Sprint 27.8 docs 2026-03-26) cause conflict markers when popped. Operationally external to Sprint 31.91; flagged for operator cleanup at convenience | OPERATOR ACTION | At operator's convenience — `git stash drop` or `git stash branch <name>` |

---

## Pre-Applied Operator Decisions (Re-stated for self-containment)

| # | Decision | Lands In |
|---|---|---|
| Phase D Item 2 | EOD Pass 2 cancel-timeout failure-mode docs + test 7 | Session 1c (RESOLVED) |
| Phase D Item 3 | Health + broker-orphan double-fire dedup → Option C hybrid | Session 2b.2 (RESOLVED — production wiring deferred S5a.1+) |
| M4 cost-of-error asymmetry | Auto-clear threshold default = 5 | Session 2c.2 (RESOLVED) |
| L3 always-fire-both-alerts | Aggregate at ≥10 + per-symbol always fire | Session 2d (RESOLVED — Tests 4 + 5 lock behavior) |
| MEDIUM #13 Alpaca anti-regression | `inspect.getsource` check (not line-number-based) | Session 5b |
| HIGH #1 auto-resolution policy | Explicit per-alert-type predicates (8 entries) | Session 5a.2 |
| HIGH #4 decomposed live-enable gate | 4 criteria (1, 2, 3a, 3b) | Session 4 (NEXT after S3) |

---

## Operator Decisions Log (Mid-Sprint)

### 2026-04-27 — Phase D Item 6: Interim Merge Timing → Option C

merge after 1c (already done); KEEP operator daily flatten as belt-and-suspenders.

### 2026-04-27 — Daily-Flatten Cessation Criteria → Conservative

Daily-flatten continues until ALL of:
1. ✅ Session 2d landed and CLEAR (SATISFIED 2026-04-28)
2. ❌ Session 3 landed and CLEAR (pending)
3. ❌ Session 4 landed and CLEAR (pending)
4. ❌ Sprint 31.91 sealed (pending)
5. ❌ 5 paper sessions post-seal showing clean mass-balance + zero broker-orphan SHORTs surviving reconcile (pending)

### 2026-04-27 — `_OCA_TYPE_BRACKET` doc-sync routing → bundle into sprint-end

Already landed in Tier 3 #1 doc-sync per `df48e31`.

### 2026-04-27 — Per-Session Register Discipline → adopt + formalize in metarepo

ARGUS register at `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md`. Workflow metarepo amendment at commit `606934e` (workflow v1.2.0).

### 2026-04-28 — DEF-216 fix-now decision → impromptu hotfix between S2c.2 and S2d

Operator chose to fix the ET-midnight rollover flake immediately rather than file-and-defer. Hotfix landed in `c36a30c`.

---

## Apr 27 Paper-Session Debrief Findings (Folded into Tier 3 #1 doc-sync)

**CRITICAL FRAMING:** Apr 27 ran on a pre-`bf7b869` commit. **First OCA-effective paper session is Apr 28 or later.**

| Finding | Routing |
|---|---|
| Finding 1 — EOD verification timing race + side-blind classification | DEF-214; Session 5a.1 Requirement 0.5 |
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

---

## 5a.1 Emitter-Site Tracking (For Pre-Flight Check 7 Migration)

`SystemAlertEvent.metadata` schema field exists post-S2b.1. S5a.1 Pre-Flight Check 7's "If the field IS present, skip Requirement 0" branch is now active.

| Site | File | Approximate location | Source session | Migration burden on S5a.1? |
|---|---|---|---|---|
| Databento dead-feed emitter | `argus/data/databento_data_service.py:279` | (pre-existing) | Pre-Sprint-31.91 | YES — S5a.1 must migrate |
| `_emit_cancel_propagation_timeout_alert` (3 invocations) | `argus/execution/order_manager.py:2163` (helper) | `_flatten_unknown_position`, `_drain_startup_flatten_queue`, `reconstruct_from_broker` | S1c | YES — S5a.1 must migrate |
| `_handle_broker_orphan_short` (`phantom_short`) | `argus/execution/order_manager.py:2204+` | Reconciliation broker-orphan branch | S2b.1 | NO — populates `metadata` from day one |
| `_handle_broker_orphan_long` (`stranded_broker_long`) | `argus/execution/order_manager.py:2204+` | Reconciliation broker-orphan branch | S2b.1 | NO — populates `metadata` from day one |
| Health integrity-check `phantom_short` | `argus/core/health.py:551-572` | `_run_daily_integrity_check` | S2b.2 | NO — populates `metadata` from day one |
| EOD Pass 2 `phantom_short` | `argus/execution/order_manager.py:1862-1878` | `eod_flatten` (post-`logger.error` in `elif side == OrderSide.SELL:` branch) | S2b.2 | NO — populates `metadata` from day one |
| **Aggregate `phantom_short_startup_engaged`** | `argus/main.py:1098-1120` | Startup-emission block (lifespan layer) | S2d | NO — populates `metadata` from day one |
| **Per-symbol `phantom_short` from startup rehydration** | `argus/main.py:1125-1141` | Startup-emission block (lifespan layer) | S2d | NO — populates `metadata={"symbol":..., "side":"SELL", "detection_source":"startup.rehydration"}` from day one |

**Atomic-migration scope for S5a.1 (Requirement 0):** the 2 pre-existing emitters above (Databento dead-feed + `_emit_cancel_propagation_timeout_alert`).

**Additional pre-flight responsibilities for S5a.1:**
1. Invoke `health_monitor.set_order_manager(self.order_manager)` when wiring HealthMonitor at startup (Option C cross-reference production activation per S2b.2 carry-forward)
2. Subscribe HealthMonitor to `SystemAlertEvent` per its own scope (Requirement 1)

---

## SQLite Storage (Sprint 31.91 New Surfaces)

| File | Source session | Schema | Purpose |
|---|---|---|---|
| `data/operations.db` | S2c.1 (NEW) | `phantom_short_gated_symbols` table (5 columns: `symbol PRIMARY KEY`, `engaged_at_utc`, `engaged_at_et`, `engagement_source`, `last_observed_short_shares`) | Persists per-symbol entry-gate state across ARGUS restarts |
| `data/operations.db` | S2d (EXTENDED) | `phantom_short_override_audit` table (8 columns: `id` autoincrement PK, `timestamp_utc`, `timestamp_et`, `symbol`, `prior_engagement_source`, `prior_engagement_alert_id`, `reason_text`, `override_payload_json`) + 2 indexes (symbol, timestamp_utc) | Forensic audit log of all operator overrides — append-only forever per Sprint 31.91 retention spec |

Sprint-end doc-sync MUST surface both tables in `architecture.md` storage table + `live-operations.md` operational reference.

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
11. ✅ Impromptu hotfix DEF-216 (test_get_regime_summary ET-midnight rollover) — CLEAR, commit `c36a30c`
12. ✅ Session 2d (operator override API + audit-log + L3 always-both startup alerts + L15 configurable threshold + B22 runbook) — CLEAR, commit `93f56cd`. **DEC-385 materialized; Track B COMPLETE.**
13. ⏳ **Session 3 (DEF-158 retry side-check + severity fix)** ← NEXT
14. Session 4 (mass-balance categorized + IMSR replay + decomposed live-enable gate)
15. Session 5a.1 (HealthMonitor consumer + REST + acknowledgment) — sprint-gating DEF-213 (atomic-migration half) + DEF-214; ALSO must invoke `health_monitor.set_order_manager()` for Option C cross-reference production wiring
16. Session 5a.2 (WebSocket + persistence + auto-resolution + retention/migration)
17. Session 5b (IBKR emitter TODOs + E2E + Alpaca behavioral check)
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
- **DEC-385 documentation (MATERIALIZED at S2d; needs writing to `decision-log.md` at sprint-end)**
- DEC-388 documentation (materializing at Session 5e)
- All 7 DEFs filed in this sprint integrated into CLAUDE.md (DEF-209/211/212/213/214/215/216)
- DEF-213 final-resolved status (schema half S2b.1 + atomic-migration half S5a.1)
- DEF-216 marked RESOLVED via impromptu hotfix `c36a30c`
- RSK-DEC-386-DOCSTRING in `risk-register.md`
- Architecture.md §3.3 + §3.7 OCA architecture (already done; verify) + §14 alert observability (new) + §X side-aware reconciliation contract per DEC-385 (new)
- **Architecture.md storage table:** add both `data/operations.db` tables (`phantom_short_gated_symbols` from S2c.1; `phantom_short_override_audit` from S2d)
- Architecture catalog `**reconciliation**` block in §4 REST endpoint catalog (already done in S2d; verify)
- `live-operations.md` updates: OCA architecture operations section (already done; verify), DEF-214 EOD verification fix runbook, DEF-215 deferred revisit trigger, **conservative daily-flatten cessation criteria + revisit decision**, alert observability acknowledgment runbook, broker-orphan-LONG M2 exp-backoff schedule documentation, **3-site phantom_short emission taxonomy** + 2 startup emission sites (reconciliation / health.integrity_check / eod_flatten / startup.aggregate / startup.per-symbol), **B22 runbook for operator override** (already done in S2d; verify)
- `pre-live-transition-checklist.md`: Session 5a.1 as HARD live-trading prerequisite (already done; verify)
- Session 5a.1 amendment header documenting Tier 3 #1-driven additions (already done; verify)
- Apr 27 debrief findings folded (already done; verify)
- Sprint-history.md entry for Sprint 31.91 (covers S0–S5e + 1 Tier 3 + 1 impromptu)
- Pass 1 retry SELL `phantom_short` alert extension follow-up (consistency-gap, not bug — deferred to future session)

---

*End Sprint 31.91 Work Journal Register.*
