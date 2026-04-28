# Sprint 31.91 — Tier 3 Architectural Review #2 (Verdict, AMENDED 2026-04-28 post-operator-disposition)

> **Verdict:** PROCEED with one structural condition (Impromptus A and B must land CLEAR before Session 5c entry).
> **Amendment date:** 2026-04-28, post-operator-disposition of routing.
> **Original verdict date:** 2026-04-28.
> **Scope:** Combined diff of Sessions 5a.1 + 5a.2 + 5b (alert-observability backend track).
> **Anchor commit:** `75c125e` on `main` (S5b Tier 2 review CLEAR_WITH_NOTES); subsequent `07070e2` is a work-journal-register refresh and does not touch any in-scope file.
> **Combined-diff base SHA:** `5f6b2a6` (post-S5a.1 register refresh).
> **Reviewer:** Claude.ai (planning instance); review conducted against `protocols/tier-3-review.md` in claude-workflow metarepo at workflow-version 1.0.1, with workflow v1.3.0 amendments (mid-sprint doc-sync coordination + structural anchors) landing in this same disposition cycle.
> **Sessions reviewed:** 5a.1 (`0236e27`), 5a.2 (`9475d91`), 5b (`b324707`).
> **Trigger:** §A1.5 of `escalation-criteria.md` — mandatory phase boundary.

## Amendment summary

The original verdict (2026-04-28) routed most surfaced DEFs as "S5c/d/e or future cleanup" or "opportunistic future." Operator disposition reviewed the routing and tightened it: items that surfaced in Sprint 31.91, touch the alert-observability backend Sprint 31.91 just sealed, and have bounded scope should be RESOLVED inside Sprint 31.91 — not deferred. This amended verdict reflects that disposition.

Changes from the original verdict:

1. **DEC-388 materialization moved from Tier 3 #2 → sprint-close.** Reason: Impromptus A+B+C (added to Sprint 31.91 by this amendment) resolve DEFs that DEC-388 cross-references. Writing DEC-388 at sprint-close after Impromptu C lands documents the final, fixed architecture rather than the architecture-with-known-defects state.
2. **DEF-217 routed to Impromptu A** (was: "S5c recommended, or impromptu before live transition").
3. **DEF-218 routed to Impromptu A** (was: "S5c/d/e or future cleanup").
4. **DEF-219 routed to Impromptu A** (was: "Bundle with DEF-217 fix").
5. **DEF-220 routed to Session 5c** (was: "S5c/d/e or future cleanup") — fold the disposition decision into S5c which already opens `AlertsConfig` territory.
6. **DEF-221 routed to Impromptu B** (was: "New sprint TBD; ideally before live transition").
7. **DEF-223 routed to Impromptu C** (was: "Future, opportunistic"). Mechanical sweep across 7 separate DBs; bounded; bundled inside the sprint while migration framework context is fresh.
8. **DEF-224 routed to Impromptu A** (was: "Future cleanup").
9. **DEF-225 routed to Impromptu A** (was: "Future test-hygiene").
10. **Conditions for Session 5c entry** changed from NONE to "Impromptus A and B landed CLEAR." DEF-217 + DEF-221 jointly establish a real, end-to-end-tested Databento auto-resolution pipeline; DEC-388's wording at sprint-close depends on these landing.
11. **Workflow protocol amendments** expanded: structural-anchor requirement (Tier 3 #1's recurrent finding) plus NEW `protocols/mid-sprint-doc-sync.md` formalizing the multi-sync coordination pattern Sprint 31.91 has established.
12. **Carry-forward map** reduced to genuine cross-sprint items only: DEF-222 (gated by future producers), DEF-175 (existing post-31.9-component-ownership scope, annotated), workflow protocol amendment (separate metarepo flow, bundled with this disposition).

The architectural verdict is unchanged: the 3-session alert-observability backend is sound. All Tier-3-surfaced concerns have bounded fixes. The operator disposition routes the bounded fixes into Sprint 31.91 rather than deferring.

## Verdict summary (unchanged from original)

The 3-session alert-observability backend is architecturally sound and ships safely. The architectural shape — `SystemAlertEvent` emitter contract with structured `metadata`, HealthMonitor as central consumer, persistence-on-consume, per-alert-type policy table with explicit `NEVER_AUTO_RESOLVE` sentinel, restart-survives via rehydrate-before-subscribe, REST + WS surface with atomic+idempotent acknowledgment, ARGUS's first migration framework — is the right architecture and is now load-bearing.

DEC-385 (S2d's side-aware reconciliation contract) is OUTSIDE Tier 3 #2's scope and remains scheduled for sprint-end doc-sync write per the existing plan. DEC-386 (Tier 3 #1's OCA architecture) is verified intact: `argus/execution/order_manager.py` was modified only in S5a.1 and only at lines `:1995-2087` (post-Pass-2 EOD verification — DEF-214) plus `:2333-2356` (`_emit_cancel_propagation_timeout_alert` metadata migration — DEF-213); both are well outside the OCA territory and the IMPROMPTU-04 fix range.

DEC-388 (alert observability architecture) **MATERIALIZES at sprint-close**, after Impromptu C lands — capturing the final architecture rather than the architecture-with-known-defects state.

## What was reviewed

The combined diff `5f6b2a6..75c125e` was inspected against the four review dimensions in `protocols/tier-3-review.md`, supplemented by direct re-reading of the resulting code state for S5a.1 contributions (since the immediate diff window post-dates S5a.1's register refresh):

1. **Architectural soundness:** the 8 layers of the backend stack — emitter contract (1), HealthMonitor consumer (2), in-memory state machine (3), SQLite persistence + rehydration (4), auto-resolution policy table (5), retention + VACUUM (6), REST surface (7), WebSocket fan-out (8) — compose cleanly. Each layer has a clear ownership boundary. No cross-layer state leak; no emitter-to-SQLite coupling.

2. **Upstream invariant preservation:** DEC-117, DEC-364, DEC-369, DEC-372 verified intact (no order_manager bracket-placement code touched). DEC-385 STRENGTHENED (single-source-of-truth coupling via threshold-provider injection). DEC-386 verified intact (cumulative `git diff --stat` of `order_manager.py` for S5a.1+S5a.2+S5b confirms zero edits to `:1670-1750` IMPROMPTU-04 region or any OCA-bracket placement code; only DEF-214 EOD verification block at `:1995-2087` and `_emit_cancel_propagation_timeout_alert` metadata at `:2333-2356` were touched, both well outside OCA territory).

3. **Falsifiable validation:** 48 new tests across the 3 sessions. Atomic-acknowledgment rollback, rehydration-before-subscribe, threshold-coupling, migration idempotence, and NEVER auto-resolve all directly exercised. All 3 Tier 2 verdicts CLEAR or CLEAR_WITH_NOTES.

4. **Failure-mode trade-offs documented:** persistence-on-consume's fire-and-forget loss window accepted as consistent with DEC-345's pattern. Predicate-handler-subscribe-before-rehydrate is informational-only today (no producers exist for the 3 deferred-emission events; rehydration loop has no `await` points).

## Validation of the operator's 14 specific items (unchanged dispositions, except where noted in Amendment Summary)

(Items 1-14 retain their Tier 3 #2 dispositions from the original verdict. DEF routing has changed per the Amendment Summary; the architectural reasoning per item stands. See original verdict text for full per-item reasoning.)

### Item 1 — `ibkr_auth_failure` E2E coverage gap
ACCEPTABLE structurally; **filed as DEF-225, routed to Impromptu A** (was: future test-hygiene).

### Item 2 — Predicate-handler subscribe-before-rehydrate
ACCEPTABLE TODAY; **filed as DEF-222, deferred to producer-wiring sprints** (unchanged — this is a genuine cross-sprint blocker; producers must land first).

### Item 3 — 6 main.py scoped exceptions accumulated this sprint
ACCEPTABLE FOR THIS SPRINT; SIGNAL FOR REFACTOR. **Fold into existing DEF-175** (post-31.9-component-ownership). Unchanged — multi-session refactor genuinely belongs in its own sprint.

### Item 4 — `acknowledgment_required_severities` gate consumer wiring still pending
**Filed as DEF-220, routed to Session 5c** (was: S5c/d/e or future cleanup). The session opens `AlertsConfig` territory naturally; resolve disposition (wire vs remove) there.

### Item 5 — `eod_residual_shorts` + `eod_flatten_failed` not in policy table
**Filed as DEF-218, routed to Impromptu A** (was: S5c/d/e or future cleanup).

### Item 6 — `HealthMonitor.set_order_manager()` production wiring still pending
ACCEPTABLE — **fold into existing DEF-175**. Unchanged.

### Item 7 — 3 deferred-emission events
RATIFY THE ARCHITECTURAL SHAPE. `DatabentoHeartbeatEvent` producer wiring **filed as DEF-221, routed to Impromptu B** (was: New sprint TBD).

### Item 8 — Migration framework introduction
RATIFY AS THE CANONICAL HOME. Adoption sweep across 7 other DBs **filed as DEF-223, routed to Impromptu C** (was: Future opportunistic).

### Item 9 — Persistence-on-consume vs persistence-on-emit
RATIFY. Unchanged.

### Item 10 — Threshold-provider injection pattern
RATIFY. Unchanged.

### Item 11 — DEC-386 OCA architecture untouched (cumulative sanity check)
VERIFIED. Unchanged.

### Item 12 — DEC-385 side-aware reconciliation contract untouched (cumulative sanity check)
VERIFIED. Unchanged.

### Item 13 — DEF-014 closure scope
PRODUCER-SIDE-RESOLVED disposition correct. Unchanged.

### Item 14 — DEC-388 reservation status
**AMENDED:** materialize at sprint-close (post-Impromptu-C), NOT at this Tier 3 #2. Reason: Impromptus A/B/C resolve DEFs that DEC-388 cross-references; documenting after their resolution gives the cleanest narrative.

## Six additional concerns surfaced (A–F) — routing AMENDED

### Concern A — Databento dead-feed alert_type producer/consumer string mismatch (CORRECTNESS DEFECT)

**SEVERITY: HIGH.** `argus/data/databento_data_service.py` Databento dead-feed emitter publishes `alert_type="max_retries_exceeded"`. The auto-resolution policy table keys on `"databento_dead_feed"`. Strings do not match. Effect: the policy entry is dead code in production — Databento dead-feed alerts persist as ACTIVE forever instead of auto-resolving on heartbeat resumption. Tests didn't catch this because the E2E test fabricates `SystemAlertEvent(alert_type="databento_dead_feed")` directly rather than driving the production emitter.

**Filed as DEF-217 with HIGH severity. Routed to Impromptu A** (paired with DEF-221 / Impromptu B for end-to-end auto-resolution verification with a real producer).

### Concern B — Policy table exhaustiveness invariant not enforced by tests

**Filed as DEF-219, routed to Impromptu A.** A regression-guard test that scans production code for `SystemAlertEvent(alert_type=<literal>)` invocations and asserts each literal is a key in the policy table would have caught Concern A and Concern D at test time. The guard belongs alongside the DEF-217 + DEF-218 fixes so that the same impromptu both fixes the bugs AND establishes the invariant that prevents recurrence.

### Concern C — `acknowledgment_required_severities` field has no consumer

**Filed as DEF-220, routed to Session 5c** (disposition decision: wire vs remove). Recommendation: removal.

### Concern D — `eod_residual_shorts` + `eod_flatten_failed` not in auto-resolution policy table

**Filed as DEF-218, routed to Impromptu A.** Suggested defaults — both `NEVER_AUTO_RESOLVE` + `operator_ack_required=True`.

### Concern E — Duplicate `_AUDIT_DDL` between route layer and migration framework

**Filed as DEF-224, routed to Impromptu A** (was: future cleanup). Bundle into Impromptu A's alert-observability hardening pass — natural fit since the migration framework IS the canonical home and Impromptu A touches all the same files.

### Concern F — `DatabentoHeartbeatEvent` producer wiring has no tracked sprint home

**Filed as DEF-221, routed to Impromptu B.** Add periodic heartbeat task to `databento_data_service.py` that publishes `DatabentoHeartbeatEvent` when the feed is healthy. Validates DEF-217 fix end-to-end.

## DEC actions

| DEC | Action |
|---|---|
| **DEC-385** | OUT OF SCOPE for Tier 3 #2. Materialized in code at S2d 2026-04-02; remains scheduled for write to `docs/decision-log.md` at sprint-end doc-sync per existing plan. |
| **DEC-386** | NO ACTION. Already written (post-Tier-3-#1). Tier 3 #2 verified intact across all 3 alert-observability sessions. |
| **DEC-388** | **MATERIALIZE AT SPRINT-CLOSE** (post-Impromptu-C, post-S5e). NOT split. NOT materialized at this Tier 3 #2. Draft text below for sprint-close doc-sync consumption. |

### DEC-388 draft text for sprint-close doc-sync

> **Title:** Alert Observability Architecture (resolves DEF-014)
> **Status:** Active. Backend complete (Sessions 5a.1+5a.2+5b, sealed by Tier 3 #2 2026-04-28); hardening complete (Impromptus A+B+C); frontend integration complete (Sessions 5c-5e).
> **Decision:** ARGUS's alert observability stack consists of: (1) `SystemAlertEvent` as the single emitter contract with structured `metadata: dict[str, Any] | None` payload (DEF-213 atomic-migration COMPLETE); (2) HealthMonitor as the central consumer maintaining in-memory `_active_alerts` + bounded `_alert_history`, persisted to `data/operations.db.alert_state`; (3) per-alert-type auto-resolution policy table (`argus/core/alert_auto_resolution.py`) with explicit `NEVER_AUTO_RESOLVE` sentinel for operator-action-required alerts, threshold-provider injection for cross-domain coupling (e.g., `phantom_short` reads `ReconciliationConfig.broker_orphan_consecutive_clear_threshold`), and 10 alert types covered (extended from 8 by Impromptu A); (4) REST surface (`/api/v1/alerts/active`, `/history`, `/{id}/acknowledge`) with snapshot-then-mutate-then-commit atomic acknowledgment + immutable `alert_acknowledgment_audit` audit-log (`audit_kind ∈ {ack, duplicate_ack, late_ack, auto_resolution}`); (5) WebSocket fan-out (`/ws/v1/alerts`) for real-time push; (6) restart-survives via `rehydrate_alerts_from_db()` invoked AFTER `HealthMonitor.start()` but BEFORE the `SystemAlertEvent` subscription; (7) retention policy + VACUUM via `asyncio.to_thread`; (8) ARGUS's first schema migration framework at `argus/data/migrations/`, append-only forward-only, transactional per-step, advisory `down`, scoped to `data/operations.db` initially, extended by Impromptu C to cover all 8 separate ARGUS SQLite DBs; (9) policy-table exhaustiveness regression guard (Impromptu A) ensures every emitted alert type has a policy entry; (10) Databento heartbeat producer (Impromptu B) provides real auto-resolution validation for the `databento_dead_feed` predicate.
> **Architectural properties:** persistence-on-consume (not persistence-on-emit); explicit-not-omission for `NEVER_AUTO_RESOLVE`; deferred-emission pattern accepted for events whose producers haven't landed (`ReconciliationCompletedEvent`, `IBKRReconnectedEvent`); fire-and-forget loss window accepted (DEC-345 lineage); production code's `SystemAlertEvent(alert_type=...)` literals must match a policy-table key (Impromptu A regression guard).
> **Alternatives considered:** persistence-on-emit (rejected: would couple every emitter to SQLite); flat list of policies vs structured table (chose table for explicit exhaustiveness); `acknowledgment_required_severities` field (removed at S5c per DEF-220 disposition — per-alert-type `operator_ack_required` is sufficient); 24h-elapsed branch in `phantom_short_startup_engaged` (kept: operator-friendly auto-archive).
> **Cross-references:** DEF-014 (RESOLVED at S5e); DEF-213 (RESOLVED at S5a.1); DEF-214 (RESOLVED at S5a.1); DEF-215 (deferred); DEF-217 (RESOLVED at Impromptu A); DEF-218 (RESOLVED at Impromptu A); DEF-219 (RESOLVED at Impromptu A); DEF-220 (RESOLVED at S5c); DEF-221 (RESOLVED at Impromptu B); DEF-222 (deferred — gated by future producers); DEF-223 (RESOLVED at Impromptu C); DEF-224 (RESOLVED at Impromptu A); DEF-225 (RESOLVED at Impromptu A); DEC-345 (separate-DB pattern, separate concern); DEC-386 (OCA architecture, separate concern, intact); DEC-385 (side-aware reconciliation contract, separate concern, intact). Tier 3 #2 verdict artifact: `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md`.

## DEF actions (AMENDED routing)

| DEF | Action | Severity | Routing |
|---|---|---|---|
| **DEF-014** | UPDATE STATUS to "PRODUCER SIDE RESOLVED at S5b; full closure at S5e (frontend)" | — | Sprint-close (after S5e) |
| **DEF-213** | CONFIRM FULLY RESOLVED. | — | Sprint-close mark |
| **DEF-214** | CONFIRM RESOLVED at S5a.1. | — | Sprint-close mark |
| **NEW DEF-217** | Databento dead-feed alert_type producer/consumer string mismatch — surgical one-line fix. | HIGH (correctness) | **Impromptu A (RESOLVED-IN-SPRINT)** |
| **NEW DEF-218** | `eod_residual_shorts` + `eod_flatten_failed` missing from auto-resolution policy table. | MEDIUM | **Impromptu A (RESOLVED-IN-SPRINT)** |
| **NEW DEF-219** | Policy table exhaustiveness invariant not enforced by tests. | MEDIUM | **Impromptu A (RESOLVED-IN-SPRINT)** |
| **NEW DEF-220** | `AlertsConfig.acknowledgment_required_severities` has no consumer. | LOW | **Session 5c (RESOLVED-IN-SPRINT)** |
| **NEW DEF-221** | `DatabentoHeartbeatEvent` producer wiring (data-layer health poller). | MEDIUM | **Impromptu B (RESOLVED-IN-SPRINT)** |
| **NEW DEF-222** | Predicate-handler subscribe-before-rehydrate audit when producers land. | MEDIUM (latent) | **DEFERRED** — gated by future producer-wiring sprint |
| **NEW DEF-223** | Migration framework adoption across 7 other separate DBs. | LOW | **Impromptu C (RESOLVED-IN-SPRINT)** |
| **NEW DEF-224** | Duplicate `_AUDIT_DDL` between routes layer and migration framework. | LOW (cleanup) | **Impromptu A (RESOLVED-IN-SPRINT)** |
| **NEW DEF-225** | `ibkr_auth_failure` dedicated E2E auto-resolution test. | LOW | **Impromptu A (RESOLVED-IN-SPRINT)** |
| **DEF-175** | ANNOTATE existing scope: (a) 6 main.py scoped exceptions accumulated in 31.91; (b) `HealthMonitor.set_order_manager()` production wiring still pending. | — | post-31.9-component-ownership (existing scope, annotated) |

**Pre-existing DEFs untouched:** DEF-204, DEF-211, DEF-212, DEF-215, DEF-209.

## Inherited follow-ups (carry-forward map — REDUCED per amendment)

The carry-forward map is now substantially smaller. Most items previously routed to "future" are folded into Sprint 31.91:

- **post-31.9-component-ownership (Sprint 31.92 successor)** — inherits DEF-175 ANNOTATED scope (6 main.py exceptions + HealthMonitor.set_order_manager() wiring); inherits DEF-222 audit if `ReconciliationCompletedEvent` producer lands here; inherits DEF-212 (`IBKRConfig` wiring into OrderManager).
- **post-31.9-reconnect-recovery (planned Sprint 31.93 successor)** — inherits DEF-211 D1+D2+D3 (existing); inherits DEF-222 audit if `IBKRReconnectedEvent` producer lands here.
- **Future test-hygiene (no specific sprint home)** — Tier 3 #1 Concerns E + F (broker-mock fixture consolidation; Test 4 `get_positions` brittleness); the `phantom_short_startup_engaged` 24h-elapsed branch E2E.
- **Sprint 35+ horizon** — DEF-209 (`Position.side` + `ManagedPosition.redundant_exit_observed` persistence); DEF-208 (live-trading test fixture).
- **Sprint 31.94 (Alpaca retirement)** — `argus/data/alpaca_data_service.py` deletion; `TestAlpacaBoundary` anti-regression test removal coordinated with retirement.

(Items previously here that are NOW IN-SPRINT: DEF-217, DEF-218, DEF-219, DEF-220, DEF-221, DEF-223, DEF-224, DEF-225.)

## Workflow protocol amendments (EXPANDED per amendment)

This Tier 3 disposition cycle bundles two distinct workflow amendments, both landing as part of the pre-impromptu doc-sync (workflow-version bump 1.2.0 → 1.3.0):

### Amendment 1 — Structural anchors over line numbers in implementation prompts

This is the SECOND Tier 3 review where stale spec line numbers surfaced (Tier 3 #1 flagged the pattern; S5b's RULE-038 disclosure made it concrete). Amendments:
- `protocols/sprint-planning.md`: implementation prompts must reference STRUCTURAL anchors (function name, regex of surrounding comment / docstring, distinctive call-pattern) rather than absolute line numbers.
- `templates/implementation-prompt.md`: replace "line range" field with "structural anchor" field; include grep-verify command block as required.
- This is the first sprint where impl prompts are produced under the new contract — the 3 new impromptu prompts (Impromptu A, B, C) and the amended S5c prompt all dogfood the new format.

### Amendment 2 — `protocols/mid-sprint-doc-sync.md` (NEW)

Sprint 31.91 has run THREE mid-sprint doc-syncs (Tier 3 #1 doc-sync, DEF-216 hotfix sync, this Tier 3 #2 sync) plus a fourth coming (sprint-close). The pattern is established and recurring; it deserves its own protocol. The new file formalizes:
- When mid-sprint syncs fire (Tier 3 verdicts surfacing materializable items, impromptu hotfixes changing DEF-table state, contradiction-discovery syncs).
- Required output: a `*-doc-sync-manifest.md` in the sprint folder enumerating every file touched + every sprint-close transition owed.
- DECs should NOT be written by mid-sprint syncs unless their full architectural narrative is complete; defer to sprint-close otherwise.
- DEFs should land in OPEN-with-routing status (not RESOLVED) at mid-sprint sync time; sprint-close transitions OPEN→RESOLVED.
- Sprint-close doc-sync prompts MUST read every `*-doc-sync-manifest.md` in the sprint folder before applying transitions.

Cross-references updated in: `bootstrap-index.md` (Protocol Index + Conversation Type table), `protocols/in-flight-triage.md` (sibling reference), `protocols/sprint-planning.md` (planning-time awareness), `protocols/tier-3-review.md` (Tier 3 verdicts produce manifests when surfacing materializable items), `protocols/impromptu-triage.md` (impromptus changing DEF-table state produce manifests), `templates/doc-sync-automation-prompt.md` (sprint-close reads manifests), `templates/work-journal-closeout.md` (manifest as required input alongside closeout artifacts), `schemas/structured-closeout-schema.md` (optional `mid_sprint_doc_sync_ref` field).

## Cross-cutting posture (unchanged)

- **Test count growth:** sprint-baseline 5,080 → post-S5b 5,232 (+152 cumulative). Healthy.
- **15 emitter sites all populating metadata:** DEF-213 atomic-migration COMPLETE.
- **Tier 2 verdict ledger:** S5a.1 CLEAR; S5a.2 CLEAR; S5b CLEAR_WITH_NOTES.
- **Per-session register discipline (workflow v1.2.0):** worked. Will work even better post-v1.3.0 with manifest coordination.
- **Operator daily-flatten cessation:** criteria #1+#2+#3 SATISFIED post-S4; criteria #4 (sprint sealed) + #5 (5 paper-sessions clean) still pending. **Tier 3 #2 amendment does NOT change cessation criteria.**

## Acceptance — Sprint 31.91 cleared with new structure

With this amended verdict landed:

- DEC-388 architectural decision DEFERRED to sprint-close (post-Impromptu-C, post-S5e); draft text included above for sprint-close doc-sync consumption.
- DEF-014 status: "PRODUCER SIDE RESOLVED; full closure at S5e."
- DEF-213/214: confirmed RESOLVED, transition at sprint-close.
- DEF-217 through DEF-225 filed in CLAUDE.md by pre-impromptu doc-sync, landing as OPEN-with-routing; sprint-close transitions to RESOLVED.
- DEF-175 annotated with main.py + set_order_manager motivators (in pre-impromptu doc-sync).
- Tier 3 #2 verdict artifact at this file location (amended).
- Workflow metarepo amendment recommendations bundled in this disposition (workflow v1.2.0 → v1.3.0).
- New `protocols/mid-sprint-doc-sync.md` formalizes the multi-sync coordination pattern.

**New session order for Sprint 31.91 (replaces prior order):**

1. ✅ Sessions 0–S5b complete (anchor `75c125e`).
2. ✅ Tier 3 #2 verdict (this artifact, amended).
3. ⏳ **Workflow metarepo amendment** (claude-workflow repo, prompt B) — bumps to v1.3.0.
4. ⏳ **ARGUS pre-impromptu doc-sync** (ARGUS repo, prompt C) — produces 3 impl prompts, amended S5c, manifest, work-journal-handoff.
5. ⏳ **Impromptu A** (alert observability hardening: DEF-217 + DEF-218 + DEF-219 + DEF-224 + DEF-225) — Tier 2 inline.
6. ⏳ **Impromptu B** (Databento heartbeat producer: DEF-221 + DEF-217 end-to-end validation) — Tier 2 inline.
7. ⏳ **Session 5c** (`useAlerts` hook + Dashboard banner + DEF-220 disposition) — Tier 2 inline.
8. ⏳ **Impromptu C** (migration framework adoption sweep: DEF-223) — Tier 2 inline.
9. ⏳ **Session 5d** (toast notifications + acknowledgment UI flow) — Tier 2 inline.
10. ⏳ **Session 5e** (Observatory alerts panel + cross-page integration) — Tier 2 inline.
11. ⏳ **Sprint-close doc-sync** — reads pre-impromptu manifest + closeouts; writes DEC-385 + DEC-388; closes DEF-014; transitions all RESOLVED-IN-SPRINT DEFs; finalizes architecture.md + sprint-history.md.

**Conditions for Session 5c entry:** Impromptus A and B must have landed CLEAR. Both establish the alert-observability backend's correctness invariants (DEF-217 string-alignment, DEF-218 policy completeness, DEF-219 exhaustiveness regression guard, DEF-221 real producer). DEC-388's sprint-close wording depends on these landing.

**Pre-live-transition gating:** DEF-217 + DEF-221 jointly establish a real, end-to-end-tested Databento auto-resolution chain. Both land in Impromptus A+B before live transition consideration.

---

*Verdict generated 2026-04-28 against `protocols/tier-3-review.md` v1.0.1.*
*Amended 2026-04-28 post-operator-disposition; references workflow v1.3.0 amendments landing in this disposition cycle.*
*Doc-sync pass commits to be referenced post-application: see `git log --grep "Tier 3 review #2 doc-sync"` and `git log --grep "workflow v1.3.0"` post-application.*
*Tier 3 review #3: not currently scheduled. Likely candidate: post-S5e sprint-close gate.*
