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
| **Refreshed at** | 2026-04-27, end-of-Session-2b.2 verdict |
| **Anchor commit** | `3542a46` (S2b.2 Tier 2 review + impl `a6846c6`) |
| **Sessions complete** | 0, 1a, 1b, 1c, 2a, 2b.1, 2b.2 |
| **Tier 3 reviews complete** | #1 (PROCEED) |
| **Active session** | None — between sessions; cleared to proceed to Session 2c.1 |
| **Sprint phase** | Track A complete (OCA architecture); Track B detection + count-filter alignment + Health observability hybrid live; per-symbol entry gate + operator override pending |
| **Workflow protocol version** | 1.2.0 (per-session register discipline formalized) |

---

## Sprint Identity (Pinned)

- **Sprint:** `sprint-31.91-reconciliation-drift`
- **Predecessor:** Sprint 31.9 (sealed 2026-04-24)
- **Mode:** HITL on `main`
- **Primary defects:** DEF-204 (reconciliation drift / phantom-short mechanism), DEF-014 (alert observability gap)
- **Operational mitigation:** Operator runs `scripts/ibkr_close_all_positions.py` daily — REQUIRED, NOT OPTIONAL per Apr 27 evidence
- **Reserved DECs at planning:** DEC-385 (side-aware reconciliation contract — Sessions 2a–2d, REMAINS RESERVED), DEC-386 (OCA-group threading + broker-only safety — MATERIALIZED at Tier 3 #1), DEC-387 (reserved but not consumed — freed), DEC-388 (alert observability architecture, resolves DEF-014 — Sessions 5a.1/5a.2/5b/5c/5d/5e)

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
| **After S2b.2** | **5,153 (+14)** | **5,192** | **866** | **+73** |

**Sprint cumulative delta:** +73 pytest, 0 Vitest.

**Test_main.py baseline:** 39 pass + 5 skip — unchanged across all sessions.

---

## DECs

### Materialized

| DEC | Description | Sessions | Status |
|---|---|---|---|
| **DEC-386** | OCA-Group Threading + Broker-Only Safety (4-layer architecture) | 0+1a+1b+1c | **Written** to `docs/decision-log.md` post-Tier-3-#1 |

### Reserved (not yet materialized)

| DEC | Description | Sessions | Materializes at |
|---|---|---|---|
| DEC-385 | Side-aware reconciliation contract | 2a (foundation) + 2b.1 (detection live) + 2b.2 (count-filter alignment + Health hybrid) → 2c.1/2c.2/2d (gate engagement + override) | Session 2d close-out |
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
| **DEF-213** | Tier 3 #1 Concern C | `SystemAlertEvent.metadata` schema gap. **PARTIAL-RESOLVED in S2b.1** — schema field added at `argus/core/events.py:425-433`. Atomic emitter migration of 2 pre-existing emitters remains S5a.1 scope | **Sprint 31.91 Session 5a.1 sprint-gating** (atomic-migration half only) | Sprint 31.91 Session 5a.1 |
| **DEF-214** | Apr 27 debrief Finding 1 | EOD verification timing race + side-blind classification | **Sprint 31.91 Session 5a.1 sprint-gating** — Requirement 0.5 | Sprint 31.91 Session 5a.1 |
| **DEF-215** | Apr 27 debrief Finding 2 | Reconciliation per-cycle log spam | DEFERRED with sharp revisit trigger | Deferred |

### Filed pre-Sprint 31.91, status unchanged

| DEF | Status |
|---|---|
| DEF-204 | Reconciliation drift / phantom-short mechanism — **detection layer + count-filter layer LIVE post-S2b.2**; per-symbol entry gate (2c.1), operator override (2d), DEF-158 retry-path side-check (3) still pending |
| DEF-014 | Alert observability gap — RESOLVES at Session 5e |
| DEF-158 | Flatten retry side-blindness — RESOLVES in Session 3 |
| DEF-199 | EOD Pass 2 A1 fix preserved — UNCHANGED across S0–S2b.2 (byte-identical except documented appended alert emission inside SELL branch in S2b.2) |

### Anticipated but NOT filed

| Anticipated DEF | Reason not filed |
|---|---|
| DEF-208 | No fresh evidence requiring filing through S2b.2 |
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
| Phase D Item 2 (EOD Pass 2 cancel-timeout failure-mode docs + test 7) | S1c | RESOLVED — Test 7 |
| Broker-only path routing through `cancel_all_orders(symbol, await_propagation=True)` | S1c | RESOLVED — 3 paths gated |
| `reconstruct_from_broker` docstring update | S1c | RESOLVED |
| `_OCA_TYPE_BRACKET` doc-sync paragraph for `live-operations.md` | Tier 3 #1 doc-sync | LANDED via `df48e31` |
| Per-session register discipline formalized in workflow metarepo | S2a | LANDED — workflow v1.2.0 |
| **DEF-213 schema-extension half** | S2b.1 (PARTIAL — atomic emitter migration still S5a.1) | `SystemAlertEvent.metadata` field added |
| **2b.2 cross-component coupling on `_broker_orphan_last_alerted_cycle`** | S2b.2 (read implementation complete; production wiring deferred to S5a.1+) | `HealthMonitor._order_manager` reads dict via `getattr` defensive pattern; Option C cross-reference verified by 3 tests |
| **Spec invariant 8 wrong attribution** (Check 0 around `risk_manager.py:335` — actually max-concurrent) | S2b.2 | Disclosed and reconciled per RULE-038; Check 0 lives at `risk_manager.py:274-275`; max-concurrent at 337-356 |

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
| Failure-mode docs for `live-operations.md` "Phantom-Short Gate Diagnosis and Clearance" | TRACKED | S1c | Sprint-end doc-sync deliverable |
| B5-MILD line shift — call site `:1505-1535` spec → `:1519-1553` post-edit | LOW (acceptable) | S2a | No spec adjustment needed |
| EventBus dispatch async-via-`asyncio.create_task`; tests need `_reconcile_and_drain` helper | OBSERVATIONAL | S2b.1 | Pattern matches `test_broker_only_paths_safety.py` |
| Cycle 1-2 WARNING is unthrottled but bounded | LOW (acceptable) | S2b.1 | ThrottledLogger compliance reviewed |
| **NEW (S2b.2):** Pass 1 retry SELL detection at `order_manager.py:1777` is sibling to Pass 2 but NOT alerted with `phantom_short`. Per RULE-007, spec scoped Pattern B to Pass 2 only | LOW (consistency gap, not behavior bug) | S2b.2 Edge Case 3 | Future session can extend taxonomy. `logger.error` unchanged |
| **NEW (S2b.2):** `HealthMonitor.set_order_manager()` production wiring at startup deferred — `main.py` is do-not-modify. Tests wire via setter; cross-reference no-op until S5a.1+ | RULE-007 deferral | S2b.2 Edge Case 1 | Inline TODO at `health.py:HealthMonitor.__init__` cites S5a.1+ migration |
| **NEW (S2b.2):** Spec do-not-modify line range `:1670-1750` for `order_manager.py` does NOT actually contain SELL-detection branching it was meant to protect | LOW (spec-anchor discrepancy) | S2b.2 RULE-038 #3 | Canonical protected region: structural anchor `elif side == OrderSide.SELL:` branches at Pass 1 retry (`:1777-1810`) and Pass 2 (`:1813-1842`). Future impl prompts should reference structural anchor |
| **NEW (S2b.2):** `logger.info` breakdown lines on margin reset site previously absent | INFORMATIONAL | S2b.2 Edge Case 4 | No existing log-line assertion picks them up |

---

## Carry-Forward Watchlist (Active)

| Item | Status | Lands in |
|---|---|---|
| **Daily-flatten cessation** | Conservative criteria pinned 2026-04-27 | Sprint-end + 5 paper-session-clean window |
| Operator daily-flatten (`scripts/ibkr_close_all_positions.py`) | REQUIRED, NOT OPTIONAL | Active |
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
| 4 emitter sites at S2b.2 close (all populate `metadata` from day one — zero S5a.1 migration burden): 2b.1's `_handle_broker_orphan_short` + `_handle_broker_orphan_long`; 2b.2's `health.py` integrity-check phantom_short + `order_manager.py` EOD Pass 2 phantom_short | TRACKED for S5a.1 grep | S5a.1 |
| **NEW (S2b.2):** Pass 1 retry SELL `phantom_short` alert extension — consistency-gap follow-up | Future session | TBD |
| **NEW (S2b.2):** `HealthMonitor.set_order_manager()` production wiring at startup | Watch | S5a.1+ (when `main.py` becomes editable). 5a.1 should invoke `health_monitor.set_order_manager(self.order_manager)` in addition to its consumer subscription wiring |
| **NEW (S2b.2):** Spec do-not-modify anchor for `order_manager.py` should reference structural `elif side == OrderSide.SELL:` rather than line numbers | TRACKED | Future impl prompts |

---

## Pre-Applied Operator Decisions (Re-stated for self-containment)

| # | Decision | Lands In |
|---|---|---|
| Phase D Item 2 | EOD Pass 2 cancel-timeout failure-mode docs + test 7 | Session 1c (RESOLVED) |
| Phase D Item 3 | Health + broker-orphan double-fire dedup → Option C hybrid | Session 2b.2 (RESOLVED — Option C cross-reference live; production wiring deferred S5a.1+) |
| M4 cost-of-error asymmetry | Auto-clear threshold default = 5 | Session 2c.2 |
| L3 always-fire-both-alerts | Aggregate at ≥10 + per-symbol always fire | Session 2d |
| MEDIUM #13 Alpaca anti-regression | `inspect.getsource` check (not line-number-based) | Session 5b |
| HIGH #1 auto-resolution policy | Explicit per-alert-type predicates (8 entries) | Session 5a.2 |
| HIGH #4 decomposed live-enable gate | 4 criteria (1, 2, 3a, 3b) | Session 4 |

---

## Operator Decisions Log (Mid-Sprint)

### 2026-04-27 — Phase D Item 6: Interim Merge Timing → Option C

merge after 1c (already done); KEEP operator daily flatten as belt-and-suspenders.

### 2026-04-27 — Daily-Flatten Cessation Criteria → Conservative

Daily-flatten continues until ALL of:
1. Session 2d landed and CLEAR
2. Session 3 landed and CLEAR
3. Session 4 landed and CLEAR
4. Sprint 31.91 sealed
5. 5 paper sessions post-seal showing clean mass-balance + zero broker-orphan SHORTs surviving reconcile

### 2026-04-27 — `_OCA_TYPE_BRACKET` doc-sync routing → bundle into sprint-end

Already landed in Tier 3 #1 doc-sync per `df48e31`.

### 2026-04-27 — Per-Session Register Discipline → adopt + formalize in metarepo

ARGUS register at `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md`. Workflow metarepo amendment at commit `606934e` (workflow v1.2.0).

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

**Atomic-migration scope for S5a.1 (Requirement 0):** the 2 pre-existing emitters above (Databento dead-feed + `_emit_cancel_propagation_timeout_alert`).

**Additional pre-flight responsibility for S5a.1:** invoke `health_monitor.set_order_manager(self.order_manager)` when wiring HealthMonitor at startup, to activate Option C cross-reference in production. The setter exists post-S2b.2; tests wire it explicitly; production wiring is deferred to S5a.1+.

---

## Session Order (Sequential — Strict)

1. ✅ Session 0 (cancel_all_orders API) — CLEAR, commit `9b7246c`
2. ✅ Session 1a (bracket OCA + Error 201 defensive) — CLEAR, commit `b25b419`
3. ✅ Session 1b (standalone-SELL OCA + Error 201 graceful) — CLEAR, commit `6009397`
4. ✅ Session 1c (broker-only paths + reconstruct docstring) — CLEAR, commit `49beae2`
5. ✅ **Tier 3 #1** — PROCEED, verdict commit `df48e31`
6. ✅ Session 2a (typed reconciliation contract) — CLEAR, commit `813fc3c`
7. ✅ Session 2b.1 (broker-orphan branch + `phantom_short` alert + cycle infrastructure) — CLEAR, commit `4119608`
8. ✅ Session 2b.2 (4 count-filter sites + 1 alert-alignment site + Option C cross-reference) — CLEAR, commit `a6846c6`
9. ⏳ **Session 2c.1 (per-symbol gate + handler + SQLite + M5 rehydration ordering)** ← NEXT
10. Session 2c.2 (clear-threshold + auto-clear, default 5)
11. Session 2d (operator override API + audit-log + always-both-alerts + B22 runbook)
12. Session 3 (DEF-158 retry side-check + severity fix)
13. Session 4 (mass-balance categorized + IMSR replay + decomposed live-enable gate)
14. Session 5a.1 (HealthMonitor consumer + REST + acknowledgment) — sprint-gating DEF-213 (atomic-migration half) + DEF-214; ALSO must invoke `health_monitor.set_order_manager()` for Option C cross-reference production wiring
15. Session 5a.2 (WebSocket + persistence + auto-resolution + retention/migration)
16. Session 5b (IBKR emitter TODOs + E2E + Alpaca behavioral check)
17. **Tier 3 #2** — combined diff 5a.1+5a.2+5b
18. Session 5c (useAlerts hook + Dashboard banner)
19. Session 5d (toast notification + acknowledgment UI flow)
20. Session 5e (Observatory alerts panel + cross-page integration)
21. Sprint close-out + doc-sync handoff

---

## Sprint-End Deliverable (Forward-Looking)

When Session 5e clears, the Work Journal produces the doc-sync handoff per `templates/work-journal-closeout.md` + `templates/doc-sync-automation-prompt.md`.

**Items the sprint-end doc-sync MUST surface:**
- DEC-386 documentation (already done in Tier 3 #1 doc-sync; verify)
- DEC-385 documentation (materializing at Session 2d)
- DEC-388 documentation (materializing at Session 5e)
- All 6 DEFs filed in this sprint integrated into CLAUDE.md
- DEF-213 final-resolved status (schema half S2b.1 + atomic-migration half S5a.1)
- RSK-DEC-386-DOCSTRING in `risk-register.md`
- Architecture.md §3.3 + §3.7 OCA architecture (already done; verify) + §14 alert observability (new)
- `live-operations.md` updates: OCA architecture operations section (already done; verify), DEF-214 EOD verification fix runbook, DEF-215 deferred revisit trigger, **conservative daily-flatten cessation criteria + revisit decision**, alert observability acknowledgment runbook, broker-orphan-LONG M2 exp-backoff schedule documentation, **3-site phantom_short emission taxonomy** (reconciliation / health.integrity_check / eod_flatten — operator can route by `source` field; auto-resolution keys on `alert_type`)
- `pre-live-transition-checklist.md`: Session 5a.1 as HARD live-trading prerequisite (already done; verify)
- Session 5a.1 amendment header documenting Tier 3 #1-driven additions (already done; verify)
- Apr 27 debrief findings folded (already done; verify)
- Sprint-history.md entry for Sprint 31.91
- Pass 1 retry SELL `phantom_short` alert extension follow-up (consistency-gap, not bug — deferred to future session)

---

*End Sprint 31.91 Work Journal Register.*
