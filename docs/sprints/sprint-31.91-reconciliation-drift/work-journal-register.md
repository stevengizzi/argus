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
| **Refreshed at** | 2026-04-27, end-of-Session-2b.1 verdict |
| **Anchor commit** | `4119608` (S2b.1 broker-orphan branch + phantom_short alert) |
| **Sessions complete** | 0, 1a, 1b, 1c, 2a, 2b.1 |
| **Tier 3 reviews complete** | #1 (PROCEED) |
| **Active session** | None — between sessions; cleared to proceed to Session 2b.2 |
| **Sprint phase** | Track A complete (OCA architecture); Track B detection layer live; gate engagement + count-filter alignment pending |
| **Workflow protocol version** | 1.2.0 (per-session register discipline formalized) |

---

## Sprint Identity (Pinned)

- **Sprint:** `sprint-31.91-reconciliation-drift`
- **Predecessor:** Sprint 31.9 (sealed 2026-04-24)
- **Mode:** HITL on `main`
- **Primary defects:** DEF-204 (reconciliation drift / phantom-short mechanism), DEF-014 (alert observability gap)
- **Operational mitigation:** Operator runs `scripts/ibkr_close_all_positions.py` daily — REQUIRED, NOT OPTIONAL per Apr 27 evidence (operator forgetting cost ~$70K notional overnight on PRE-OCA code)
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
| **After S2b.1** | **5,139 (+6)** | **5,178** | **866** | **+59** |

**Sprint cumulative delta:** +59 pytest, 0 Vitest.

**Test_main.py baseline:** 39 pass + 5 skip — unchanged across all sessions.

---

## DECs

### Materialized

| DEC | Description | Sessions | Status |
|---|---|---|---|
| **DEC-386** | OCA-Group Threading + Broker-Only Safety (4-layer architecture: API contract → bracket OCA → standalone-SELL OCA → broker-only safety) | 0+1a+1b+1c | **Written** to `docs/decision-log.md` post-Tier-3-#1; Latest-DEC pointer advanced from DEC-384 → DEC-386 |

### Reserved (not yet materialized)

| DEC | Description | Sessions | Materializes at |
|---|---|---|---|
| DEC-385 | Side-aware reconciliation contract | 2a (foundation) + 2b.1 (detection live) → 2b.2/2c.1/2c.2/2d (gate + count-filter + override) | Session 2d close-out |
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
| **DEF-209** (extended) | Tier 3 #1 Concern D | `Position.side` AND `ManagedPosition.redundant_exit_observed` persistence in historical-record writers | Sprint 35+ horizon (Learning Loop V2 prereq) | Sprint 35+ |
| **DEF-211** (extended) | Pre-existing + Apr 27 Findings 3+4 | EXTENDED scope: 3 coupled deliverables D1+D2+D3 | Sprint 31.93 (sprint-gating) | Sprint 31.93 |
| **DEF-212** | Tier 3 #1 Concern B | `_OCA_TYPE_BRACKET = 1` constant drift risk | Sprint 31.92 | Sprint 31.92 |
| **DEF-213** | Tier 3 #1 Concern C | `SystemAlertEvent.metadata` schema gap. **PARTIAL-RESOLVED in S2b.1** — schema field added at `argus/core/events.py:425-433`. Atomic emitter migration of 2 pre-existing emitters (Databento dead-feed at `databento_data_service.py:279`; `_emit_cancel_propagation_timeout_alert` at `order_manager.py:2163`) remains S5a.1 scope per Pre-Flight Check 7's "skip Requirement 0" branch | **Sprint 31.91 Session 5a.1 sprint-gating** (atomic-migration half only; schema half complete) | Sprint 31.91 Session 5a.1 |
| **DEF-214** | Apr 27 debrief Finding 1 | EOD verification timing race + side-blind classification | **Sprint 31.91 Session 5a.1 sprint-gating** — Requirement 0.5 | Sprint 31.91 Session 5a.1 |
| **DEF-215** | Apr 27 debrief Finding 2 | Reconciliation per-cycle log spam | DEFERRED with sharp revisit trigger | Deferred |

### Filed pre-Sprint 31.91, status unchanged

| DEF | Status |
|---|---|
| DEF-204 | Reconciliation drift / phantom-short mechanism — **detection layer LIVE post-S2b.1**; gate engagement (2c.1), count-filter alignment (2b.2), retry-path side-check (3) still pending |
| DEF-014 | Alert observability gap — RESOLVES at Session 5e close-out |
| DEF-158 | Flatten retry side-blindness — RESOLVES in Session 3 |
| DEF-199 | EOD Pass 2 A1 fix preserved (do-not-modify region) — UNCHANGED across S0–S2b.1 |

### Anticipated but NOT filed

| Anticipated DEF | Reason not filed |
|---|---|
| DEF-208 | No fresh evidence requiring filing through S2b.1. Disposition final unless later session surfaces it. |
| DEF-210 | Same — original anticipated routing not opened by any session in flight. |

---

## Risks Filed

| RSK | Description | Time-bounded by |
|---|---|---|
| **RSK-DEC-386-DOCSTRING** | `reconstruct_from_broker()` STARTUP-ONLY contract is a docstring, not a runtime gate | Sprint 31.93 DEF-211 D1 |

---

## Resolved Carry-Forward Items (Cumulative)

| Resolved | Resolution session | Detail |
|---|---|---|
| Invariant 21 grep-guard (deferred from S0) | S1a | LANDED |
| `Order.oca_group_id` field arrival (M1 disposition) | S1a | LANDED via `Order.ocaGroup` + `Order.ocaType` |
| `ManagedPosition.oca_group_id` persistence | S1a | LANDED via `_handle_entry_fill` |
| Defensive Error 201 on T1/T2 submission preserving DEC-117 (Invariant 4) | S1a | LANDED — `_is_oca_already_filled_error()` |
| Caller-side ERROR log suppression on OCA-filled (open from S1a) | S1b | RESOLVED — `_handle_oca_already_filled` helper |
| Phase D Item 2 (EOD Pass 2 cancel-timeout failure-mode docs + test 7) | S1c | RESOLVED — Test 7 |
| Broker-only path routing through `cancel_all_orders(symbol, await_propagation=True)` | S1c | RESOLVED — 3 paths gated |
| `reconstruct_from_broker` docstring update | S1c | RESOLVED — STARTUP-ONLY contract docstring |
| `_OCA_TYPE_BRACKET` doc-sync paragraph for `live-operations.md` | Tier 3 #1 doc-sync | LANDED via `df48e31` |
| Per-session register discipline formalized in workflow metarepo | S2a | LANDED — workflow v1.2.0 |
| **DEF-213 schema-extension half** | S2b.1 (PARTIAL — atomic emitter migration still S5a.1) | `SystemAlertEvent.metadata: dict[str, Any] \| None = None` added; S5a.1 Pre-Flight Check 7 skip-Requirement-0 branch now active |

---

## Outstanding Code-Level Items (Sprint-Tracked, Not DEF-Worthy)

| Item | Severity | Source | Notes |
|---|---|---|---|
| `asyncio.get_event_loop().time()` in IBKR polling loop | LOW | S0 | Cleanup deferred until Python floor bumps to 3.12+ |
| DISCOVERY line-number anchors drifted >5 lines from spec for `place_bracket_order` and rollback path | LOW | S1a | C6 soft halt, not B5 hard halt |
| Generic Error 201 logged at WARNING (not ERROR per impl-prompt requirement) | LOW (accepted) | S1a | Pre-Sprint-31.91 baseline was WARNING |
| Simultaneous-multiple-positions-same-symbol OCA edge case | OBSERVATIONAL | S1a | Naturally handled by per-`pending` ULID derivation |
| Latent rollback-flag inconsistency under `bracket_oca_type=0` | INFORMATIONAL | S1b JC2 | Bounded by `IBKRConfig` RESTART-REQUIRED note |
| Revision-rejected fresh T1/T2 resubmissions outside original bracket OCA group | LOW (cleanup-eligible) | S1b Follow-Up #4 | Bracket OCA covers T1/T2 in normal operation |
| Failure-mode docs added to `docs/live-operations.md` "Phantom-Short Gate Diagnosis and Clearance" section | TRACKED | S1c | Sprint-end doc-sync deliverable |
| B5-MILD line shift — call site `:1505-1535` spec → `:1519-1553` post-edit (+14 lines from natural code growth) | LOW (acceptable) | S2a | No spec adjustment needed for downstream sessions |
| **NEW (S2b.1):** EventBus dispatch is async-via-`asyncio.create_task`; tests need `_reconcile_and_drain` helper that runs `await om._event_bus.drain()` after each `reconcile_positions` call | OBSERVATIONAL | S2b.1 | Pattern matches `test_broker_only_paths_safety.py:359, :421` |
| **NEW (S2b.1):** Cycle 1-2 WARNING is unthrottled but bounded (at most 2 WARNINGs per orphan symbol; resolves on broker-zero or persists into cycle ≥3 schedule) | LOW (acceptable) | S2b.1 | ThrottledLogger compliance reviewed |

---

## Carry-Forward Watchlist (Active)

| Item | Status | Lands in |
|---|---|---|
| **Daily-flatten cessation** | Conservative criteria pinned 2026-04-27 | Sprint-end + 5 paper-session-clean window |
| Operator daily-flatten (`scripts/ibkr_close_all_positions.py`) | REQUIRED, NOT OPTIONAL | Active |
| `auto_resolved` test scaffolding (5a.1 test 8) | Watch | 5a.2 (must remove) |
| Banner mount on `Dashboard.tsx` (5c) | Watch | 5e (relocate to `Layout.tsx`) |
| Toast mount on `Dashboard.tsx` (5d) | Watch | 5e (relocate to `Layout.tsx`) |
| **2b.2 cross-component coupling on `_broker_orphan_last_alerted_cycle`** | **NOW POPULATED** by 2b.1 | 2b.2 reads dict for Phase D Item 3 Option C hybrid; migration to HealthMonitor queryable state in 5a.1+ |
| `/api/v1/alerts/{id}/audit` endpoint surface | Watch | 5a.1 (verify exists), 5e (consume) |
| AlpacaBroker `_check_connected` AttributeError | DISCLOSED, out-of-scope for 31.91 | Sprint 31.94 |
| `BracketOrderResult.oca_group_id` exposure | OBSERVATIONAL | Future API-cleanliness |
| Tier 3 #1 Concern A (`_is_oca_already_filled_error` helper module abstraction leakage) | Implicit DEF-212 sibling | Sprint 31.92 |
| Tier 3 #1 Concern E (test fixture drift — `MagicMock()` brokers in 12+ files) | Test-hygiene backlog | Future test-hygiene session |
| Tier 3 #1 Concern F (Test 4 `get_positions.side_effect` brittleness) | Test-hygiene backlog | Future test-hygiene session |
| First OCA-effective paper session debrief | Watch | Apr 28 or later (first post-`bf7b869` session) |
| Spec invariant 8 wrong attribution (Check 0 around `risk_manager.py:335` — actually max-concurrent) | Watch | 2b.2 prompt handles |
| Emitter-site line-number drift in `order_manager.py` | TRACKED | S5a.1 pre-flight grep is canonical lookup |
| **NEW (S2b.1):** 2 new emitter sites added — `_handle_broker_orphan_short` (`phantom_short`) and `_handle_broker_orphan_long` (`stranded_broker_long`) at `:2204+`. Both populate `metadata` structurally from day one (no atomic-migration burden on S5a.1 for these) | TRACKED for S5a.1 grep | S5a.1 |

---

## Pre-Applied Operator Decisions (Re-stated for self-containment)

| # | Decision | Lands In |
|---|---|---|
| Phase D Item 2 | EOD Pass 2 cancel-timeout failure-mode docs + test 7 | Session 1c (RESOLVED) |
| Phase D Item 3 | Health + broker-orphan double-fire dedup → Option C hybrid (both fire; cross-reference via `_broker_orphan_last_alerted_cycle`) | Session 2b.2 (dict now populated by 2b.1) |
| M4 cost-of-error asymmetry | Auto-clear threshold default = 5 | Session 2c.2 |
| L3 always-fire-both-alerts | Aggregate at ≥10 + per-symbol always fire (no suppression) | Session 2d |
| MEDIUM #13 Alpaca anti-regression | `inspect.getsource` check (not line-number-based) | Session 5b |
| HIGH #1 auto-resolution policy | Explicit per-alert-type predicates (8 entries) | Session 5a.2 |
| HIGH #4 decomposed live-enable gate | 4 criteria (1, 2, 3a, 3b) | Session 4 |

---

## Operator Decisions Log (Mid-Sprint)

### 2026-04-27 — Phase D Item 6: Interim Merge Timing → Option C

**Decision:** merge after 1c (already done); KEEP operator daily flatten as belt-and-suspenders.

### 2026-04-27 — Daily-Flatten Cessation Criteria → Conservative

**Conservative cessation criteria — daily-flatten continues until ALL of:**
1. Session 2d landed and CLEAR (architectural core complete — side-aware reconciliation contract)
2. Session 3 landed and CLEAR (DEF-158 retry path side-aware)
3. Session 4 landed and CLEAR (mass-balance assertion live as continuous proof)
4. Sprint 31.91 sealed (doc-sync complete, all DEFs filed/resolved)
5. 5 paper sessions post-seal showing clean mass-balance + zero broker-orphan SHORTs surviving reconcile

**Sprint-end deliverable:** Doc-sync into `docs/live-operations.md` and `CLAUDE.md` at sprint-end.

### 2026-04-27 — `_OCA_TYPE_BRACKET` doc-sync routing → bundle into sprint-end

Already landed in Tier 3 #1 doc-sync per `df48e31`.

### 2026-04-27 — Per-Session Register Discipline → adopt + formalize in metarepo

ARGUS register artifact at `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md`. Workflow metarepo amendment at commit `606934e` (workflow v1.2.0); ARGUS submodule pointer bumped to match.

---

## Apr 27 Paper-Session Debrief Findings (Folded into Tier 3 #1 doc-sync)

**CRITICAL FRAMING:** Apr 27 ran on a pre-`bf7b869` commit. Sessions 0/1a/1b/1c had not yet landed. Apr 27's 43-symbol short cascade is another DEF-204 manifestation on the same pre-fix code that produced Apr 22-24 cascades — NOT a test of OCA architecture coverage. **First OCA-effective paper session is Apr 28 or later.**

| Finding | Routing |
|---|---|
| Finding 1 — EOD verification timing race + side-blind classification | DEF-214; Session 5a.1 Requirement 0.5 |
| Finding 2 — Reconciliation per-cycle log spam | DEF-215; deferred with sharp revisit trigger |
| Finding 3 — `max_concurrent_positions` counts broker-only longs | Folded into DEF-211 extended scope (deliverable D3) |
| Finding 4 — Boot-time reconciliation policy + IMPROMPTU-04 gate | Folded into DEF-211 extended scope (D2 + D3) |

---

## Tier 3 Reviews

### Tier 3 #1 — PROCEED (2026-04-27)

- **Anchor commit:** `bf7b869` on `main`
- **Combined-diff scope:** Sessions 0+1a+1b+1c (OCA architecture track)
- **Verdict artifact:** `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md` (commit `df48e31`)
- **Workflow protocol amendment:** `protocols/tier-3-review.md` 1.0.0 → 1.0.1; submodule pointer in ARGUS bumped to `3732036` via commit `6b942e5`
- **Outcomes:** DEC-386 written; DEFs 209/211/212/213/214/215 filed; RSK-DEC-386-DOCSTRING filed; Session 5a.1 impl prompt amended; 10 doc files updated

### Tier 3 #2 — Pending

- **Anticipated:** After Session 5b lands (combined diff 5a.1+5a.2+5b — alert observability backend)

---

## 5a.1 Emitter-Site Tracking (For Pre-Flight Check 7 Migration)

Per Tier 3 #1 doc-sync DEF-213 amendment, S5a.1's pre-flight grep enumerates `SystemAlertEvent(` emitter sites for atomic schema migration. Live state at S2b.1 close:

| Site | File | Approximate location | Source session | Migration burden on S5a.1? |
|---|---|---|---|---|
| Databento dead-feed emitter | `argus/data/databento_data_service.py:279` | (pre-existing) | Pre-Sprint-31.91 | YES — S5a.1 must migrate to populate `metadata` |
| `_emit_cancel_propagation_timeout_alert` (3 invocations) | `argus/execution/order_manager.py:2163` (helper) | `_flatten_unknown_position`, `_drain_startup_flatten_queue`, `reconstruct_from_broker` | S1c | YES — S5a.1 must migrate to populate `metadata` |
| `_handle_broker_orphan_short` (`phantom_short`) | `argus/execution/order_manager.py:2204+` | Reconciliation broker-orphan branch | S2b.1 | NO — populates `metadata` from day one |
| `_handle_broker_orphan_long` (`stranded_broker_long`) | `argus/execution/order_manager.py:2204+` | Reconciliation broker-orphan branch | S2b.1 | NO — populates `metadata` from day one |

**`SystemAlertEvent.metadata` schema field exists post-S2b.1** at `argus/core/events.py:425-433`. S5a.1 Pre-Flight Check 7's "If the field IS present, skip Requirement 0 and proceed to Requirement 1" branch is now active.

**Atomic-migration scope for S5a.1 (Requirement 0):** the 2 pre-existing emitters above (Databento dead-feed + `_emit_cancel_propagation_timeout_alert`). Plus any emitters added by S2b.2/S2c.1/S2d/S3 that don't populate `metadata` from day one — register will track each addition.

---

## Session Order (Sequential — Strict)

1. ✅ Session 0 (cancel_all_orders API) — CLEAR, commit `9b7246c`
2. ✅ Session 1a (bracket OCA + Error 201 defensive) — CLEAR, commit `b25b419`
3. ✅ Session 1b (standalone-SELL OCA + Error 201 graceful) — CLEAR, commit `6009397`
4. ✅ Session 1c (broker-only paths + reconstruct docstring) — CLEAR, commit `49beae2`
5. ✅ **Tier 3 #1** — PROCEED, verdict commit `df48e31`
6. ✅ Session 2a (typed reconciliation contract) — CLEAR, commit `813fc3c`
7. ✅ Session 2b.1 (broker-orphan branch + `phantom_short` alert + cycle infrastructure) — CLEAR, commit `4119608`
8. ⏳ **Session 2b.2 (4 count-filter sites + 1 alert-alignment site)** ← NEXT
9. Session 2c.1 (per-symbol gate + handler + SQLite + M5 rehydration ordering)
10. Session 2c.2 (clear-threshold + auto-clear, default 5)
11. Session 2d (operator override API + audit-log + always-both-alerts + B22 runbook)
12. Session 3 (DEF-158 retry side-check + severity fix)
13. Session 4 (mass-balance categorized + IMSR replay + decomposed live-enable gate)
14. Session 5a.1 (HealthMonitor consumer + REST + acknowledgment) — sprint-gating DEF-213 (atomic-migration half) + DEF-214
15. Session 5a.2 (WebSocket + persistence + auto-resolution + retention/migration)
16. Session 5b (IBKR emitter TODOs + E2E + Alpaca behavioral check)
17. **Tier 3 #2** — combined diff 5a.1+5a.2+5b
18. Session 5c (useAlerts hook + Dashboard banner)
19. Session 5d (toast notification + acknowledgment UI flow)
20. Session 5e (Observatory alerts panel + cross-page integration)
21. Sprint close-out + doc-sync handoff

---

## Sprint-End Deliverable (Forward-Looking)

When Session 5e clears, the Work Journal produces the doc-sync handoff per `templates/work-journal-closeout.md` (standard top-half) + `templates/doc-sync-automation-prompt.md`.

**Items the sprint-end doc-sync MUST surface:**
- DEC-386 documentation (already done in Tier 3 #1 doc-sync; verify)
- DEC-385 documentation (materializing at Session 2d)
- DEC-388 documentation (materializing at Session 5e)
- All 6 DEFs filed in this sprint integrated into CLAUDE.md
- DEF-213 final-resolved status (schema half S2b.1 + atomic-migration half S5a.1)
- RSK-DEC-386-DOCSTRING in `risk-register.md`
- Architecture.md §3.3 + §3.7 OCA architecture (already done; verify) + §14 alert observability (new)
- `live-operations.md` updates: OCA architecture operations section (already done; verify), DEF-214 EOD verification fix runbook, DEF-215 deferred revisit trigger, **conservative daily-flatten cessation criteria + revisit decision**, alert observability acknowledgment runbook, broker-orphan-LONG M2 exp-backoff schedule documentation
- `pre-live-transition-checklist.md`: Session 5a.1 as HARD live-trading prerequisite (already done; verify)
- Session 5a.1 amendment header documenting Tier 3 #1-driven additions (already done; verify)
- Apr 27 debrief findings folded (already done; verify)
- Sprint-history.md entry for Sprint 31.91

---

*End Sprint 31.91 Work Journal Register.*
