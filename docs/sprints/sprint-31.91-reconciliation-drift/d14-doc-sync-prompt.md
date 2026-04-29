# Sprint 31.91 Doc Sync (D14)

## Instructions

You are performing documentation synchronization after the completed Sprint 31.91. **This is a documentation-only session.** Do NOT modify any source code, tests, or configuration files. Only modify documentation files.

Follow the doc-sync skill in `.claude/skills/doc-sync.md` as the primary operational reference.

**Anchor commit:** `4c737d5` on `main` (post-Session-5e + post-catalog-hotfix; CI green)

**Sprint mode:** Human-in-the-loop, single coordination surface (Work Journal conversation in Claude.ai); all sessions executed serially against `main`.

---

## Pre-Sync: Read Mid-Sprint Manifests + Disposition Matrix

Before applying any transitions, perform these reads in order:

### 1. List and read every mid-sprint doc-sync manifest in the sprint folder

```bash
ls docs/sprints/sprint-31.91-reconciliation-drift/*-doc-sync-manifest.md
```

For Sprint 31.91, the only manifest is:

- `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md` (committed at `948b978`)

For each manifest:

1. Read in full.
2. Extract the "DEF transitions owed at sprint-close" table.
3. Extract the "DECs deferred to sprint-close" table.
4. Extract the "Architecture / catalog freshness items deferred to sprint-close" table.
5. Verify each claimed transition against actual sprint state:
   - **DEF transitions:** confirm the owning session/impromptu close-out landed CLEAR. If not, the DEF stays OPEN; surface in sprint-close output.
   - **DEC writes:** confirm the cross-references are now resolvable (DEFs resolved, sessions complete).
   - **Catalog freshness items:** confirm the underlying surfaces exist as expected.
6. Build the consolidated transition list as input to the rest of the doc-sync.

If any manifest is malformed or claims transitions inconsistent with sprint state, **HALT and surface to operator**. Do not proceed with partial transitions.

The mid-sync protocol that produces these manifests is `protocols/mid-sprint-doc-sync.md` v1.0.0.

### 2. Read the DEF Disposition Matrix

```bash
cat docs/sprints/sprint-31.91-reconciliation-drift/def-disposition-matrix.md
```

This matrix is the **canonical routing reference** for every open carry-forward item from Sprint 31.91. It documents:

- 13 DEFs RESOLVED-IN-SPRINT (transitions to apply)
- 5 new DEFs filed in-sprint (DEF-226/227/228/229/230)
- 6 pre-existing DEFs touched but unchanged (routing language for each)
- ~25 reviewer/code-level carry-forward items with confidence-graded routing
- 4 process-improvement observations (F.1 through F.4)

When updating CLAUDE.md DEF table entries, **use the matrix's routing language verbatim where possible** — it has been calibrated to avoid over-precision while preserving useful routing signal.

### 3. Read the work-journal-register

```bash
cat docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
```

The register is the **structured truth** behind this prompt's embedded close-out content. If anything in this prompt's embedded close-out conflicts with the register, the register is authoritative — the prompt was hand-written from the register and may have transcription drift.

### 4. Inventory all 25 session closeout files + 2 hotfix references

```bash
ls docs/sprints/sprint-31.91-reconciliation-drift/session-*-closeout.md
ls docs/sprints/sprint-31.91-reconciliation-drift/impromptu-*-closeout.md
```

These contain the per-session ground truth for any claim you cannot verify from the manifest or register alone. The two in-sprint hotfixes (`c36a30c` for DEF-216 ET-midnight rollover; `4c737d5` for post-S5e catalog freshness) do not have dedicated closeout files — they are documented inline in the register and (for `c36a30c`) in the session-2c.2 closeout's hotfix annotation.

---

## Sprint Summary

- **Sprint:** 31.91 — Reconciliation drift / phantom-short fix + alert observability completion
- **Mode:** HITL on `main`
- **Sessions completed:** 25 implementation sessions + 2 Tier 3 reviews + 2 in-sprint hotfixes
- **Session list:** S0, S1a, S1b, S1c, S2a, S2b.1, S2b.2, S2c.1, S2c.2 (+ DEF-216 hotfix `c36a30c`), S2d, S3, S4, S5a.1, S5a.2, S5b, Impromptu A, Impromptu B, S5c, Impromptu C, S5d, S5e (+ catalog hotfix `4c737d5`)
- **Tier 3 reviews:** #1 PROCEED (DEC-386 materialized); #2 PROCEED-with-conditions, AMENDED 2026-04-28 (DEC-388 deferred to sprint-close per Pattern B)
- **Test count:** pytest **5,080 → 5,269** (+189); Vitest **866 → 913** (+47)
- **Files changed across sprint:** ~120+ (source + tests + docs + config)
- **Anchor commit at sprint close:** `4c737d5`
- **CI status:** Green on `4c737d5` (verified by operator post-hotfix)

### Mid-sprint doc-syncs in this sprint

- **Pre-impromptu doc-sync** (2026-04-22, manifest at `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md`, commit `948b978`):
  - 13 DEF transitions claimed (DEF-014 + DEF-158 + DEF-213 + DEF-214 + DEF-216 + DEF-217 + DEF-218 + DEF-219 + DEF-220 + DEF-221 + DEF-223 + DEF-224 + DEF-225)
  - 2 DEC deferrals to sprint-close (DEC-385 from S2d; DEC-388 spanning S5a.1+S5a.2+S5b+Impromptus A+B+C+S5c+S5d+S5e)
  - All transitions to be applied at this D14 doc-sync.

No additional mid-syncs occurred — Tier 3 #2's amended verdict on 2026-04-28 deferred DEC-388 to sprint-close (Pattern B per `protocols/mid-sprint-doc-sync.md` v1.0.0) rather than firing a new mid-sync.

---

## Sprint Summary Narrative (For sprint-history.md Entry)

> Use this narrative verbatim or as a tight starting point for the Sprint 31.91 entry in `docs/sprint-history.md`. Adapt formatting to match the file's existing per-sprint section style.

### Sprint 31.91 — Reconciliation Drift / Phantom-Short Fix + Alert Observability Completion

**Goal:** Resolve DEF-204 reconciliation drift (phantom-short cascades observed on Apr 24, 2026) by threading OCA-group identifiers through bracket-order placement and adding broker-only safety; close DEF-014 alert observability gap by completing the full producer→consumer→storage→REST→WS→frontend pipeline. Secondary goal: harden the alert observability pipeline against the Tier 3 #2 concerns surfaced during architectural review.

**Outcome:** Both primary defects RESOLVED. **DEF-204 mechanism architecturally closed** by 4-layer DEC-386 (OCA-Group Threading + Broker-Only Safety, Tier 3 #1 verdict 2026-04-27) plus 6-layer DEC-385 (Side-Aware Reconciliation Contract, S2d) plus S3's flatten-retry side-blindness fix (DEF-158 RESOLVED) plus S4's falsifiable validation infrastructure. **DEF-014 FULLY RESOLVED** at S5e via the alert observability pipeline spanning S5a.1 (storage + restart recovery via SQLite migration framework), S5a.2 (auto-resolution policy table for 11+ alert types; expanded to 13 entries post-Impromptu-A), S5b (IBKR producer wiring at `_reconnect()` end-of-retries + `_on_error()` CRITICAL non-connection else-branch), Impromptus A+B+C (backend hardening + producer wiring + migration framework adoption across all 8 ARGUS SQLite DBs), S5c (frontend Layer 1: `useAlerts` hook + Dashboard banner), S5d (frontend Layer 2: toast + ack-error modal), and S5e (frontend Layer 3: Observatory `AlertsPanel` + cross-page mount in `AppShell.tsx` + RULE-007 scope-expanded `/audit` endpoint).

**Architectural decisions:** DEC-385 (Side-Aware Reconciliation Contract — 6 layers covering main.py call-site, OrderManager Pass 1 + Pass 2 + EOD verify polling, side-aware classification, audit-log enrichment); DEC-386 (OCA-Group Threading + Broker-Only Safety — 4 layers closing ~98% of DEF-204's mechanism, Tier 3 #1 verdict); DEC-388 (Alert Observability Architecture — multi-emitter consumer pattern with HealthMonitor as central consumer, per-alert-type auto-resolution policy table, SQLite-backed restart recovery, frontend banner + toast + Observatory panel, scope-expanded `/audit` endpoint).

**DEFs RESOLVED-IN-SPRINT:** DEF-014 (PRIMARY DEFECT: alert observability gap, S5a.1+S5a.2+S5b+Impromptus A+B+C+S5c+S5d+S5e), DEF-158 (flatten retry side-blindness, S3), DEF-213 (SystemAlertEvent.metadata schema, S2b.1+S5a.1), DEF-214 (EOD verify polling, S5a.1), DEF-216 (test_get_regime_summary ET-midnight race, impromptu hotfix `c36a30c`), DEF-217/218/219 (Tier 3 #2 Concerns A/D/B alert hardening, Impromptu A), DEF-220 (acknowledgment_required_severities consumer wiring, Option A REMOVAL via S5c), DEF-221 (DatabentoHeartbeatEvent producer, Impromptu B), DEF-223 (migration framework adoption sweep across 7 separate DBs, Impromptu C), DEF-224 (DDL deduplication, Impromptu A), DEF-225 (ibkr_auth_failure dedicated E2E test, Impromptu A).

**New DEFs filed:** DEF-226 (full focus-trap on AlertAcknowledgmentModal, S5d), DEF-227 (auth-context operator_id wiring, S5d, BLOCKED on auth context infrastructure), DEF-228 (backend `/history` `until` query parameter, S5e), DEF-229 (Observatory pagination virtualization for AlertsPanel, S5e), DEF-230 (audit-loading state and error-toast for `useAlertAuditTrail`, S5e). All five are LOW priority opportunistic deferrals with explicit triggers — see `def-disposition-matrix.md` for routing.

**RSK filed:** RSK-DEC-386-DOCSTRING (bounded by Sprint 31.93 DEF-211 D1 — converts STARTUP-ONLY contract from docstring to runtime gate).

**Migration framework:** All 8 ARGUS SQLite DBs are now framework-managed (operations.db at S5a.2 foundational; catalyst + evaluation + regime_history + learning + vix_landscape + counterfactual + experiments at Impromptu C). Each DB has migration v1 codifying existing schema as-of Sprint 31.91 Impromptu C, including columns from prior in-place ALTERs (catalyst.fetched_at from Sprint 23.6; regime_snapshots.vix_close from Sprint 27.9; counterfactual variant_id from Sprint 32.5 S5; counterfactual scoring_fingerprint from FIX-01; experiments variants.exit_overrides from Sprint 32.5 S1). Sprint-spec D16 fulfilled.

**Operational mitigation in effect during sprint:** Operator ran `scripts/ibkr_close_all_positions.py` daily as belt-and-suspenders mitigation against DEF-204 mechanism. Cessation criteria: (1) DEC-386 architecture LIVE ✅ (Tier 3 #1 PROCEED); (2) DEC-385 contract LIVE ✅ (S2d); (3) Falsifiable validation infrastructure LIVE ✅ (S4); (4) Sprint sealed ✅ (this D14 doc-sync); (5) 5 paper sessions clean post-sprint-seal — pending. Daily-flatten cessation will be evaluated after criterion #5 is met.

**Tier 3 reviews:** Tier 3 #1 PROCEED for DEC-386 OCA architecture (2026-04-27). Tier 3 #2 PROCEED-with-conditions AMENDED on 2026-04-28 — DEC-388 deferred to sprint-close per Pattern B; 9 new DEFs filed (DEF-217 through DEF-225), of which 8 RESOLVED-IN-SPRINT via Impromptus A+B+C and S5c, with DEF-222 alone deferred (subscribe-before-rehydrate audit, gated on first producer-wiring sprint).

**In-sprint hotfixes:** Two impromptu hotfixes during the sprint — `c36a30c` (DEF-216 test_get_regime_summary ET-midnight rollover race, between S2c.2 and S2d) and `4c737d5` (post-S5e API catalog freshness regeneration for `GET /api/v1/alerts/{alert_id}/audit`). Both single-commit, mechanical fixes with no Tier 2 review needed; the latter surfaced a sprint-wide observation about DEC-328 full-suite-at-Tier-1 process discipline.

**Process discipline metrics:** 18 work-journal-register refreshes absorbed without conversation drift; 8 consecutive sessions with closeout `tests_added` claims matching actual delta; 6 `main.py` scoped exceptions documented across the sprint (all backend-layer; finalized at S5a.2); RULE-038 drift count ranged from 2 (S5b) to 7 (S5d) per session, all reviewer-verified, none materially scope-changing — already addressed by `templates/implementation-prompt.md` v1.5.0 structural-anchor amendment 2026-04-28.

**Tests:** pytest 5,080 → 5,269 (+189); Vitest 866 → 913 (+47).

**Sprint folder canonical artifacts:** `def-disposition-matrix.md` (D14 routing reference), `work-journal-register.md` (final state), `pre-impromptu-doc-sync-manifest.md` (mid-sprint manifest), `tier-3-review-1-verdict.md`, `tier-3-review-2-verdict.md`, plus 25 session closeouts + 25 session reviews.

---

## Doc Update Checklist

The following files MUST be updated. For each file, the action plan describes the changes needed; you will derive surgical find-and-replace strings against current file content.

### File 1: `CLAUDE.md`

**Test count baseline refresh:**
- Update test count from `5,080` to `5,269` pytest
- Update Vitest count from `866` to `913`
- Update sprint count: ARGUS now has Sprint 31.91 in the completed list

**DEF table updates:** 18 changes total.

**13 DEFs to mark RESOLVED-IN-SPRINT** (apply transitions per `pre-impromptu-doc-sync-manifest.md`):

| DEF | Resolution | Anchor |
|---|---|---|
| DEF-014 | RESOLVED via Sprint 31.91 (S5a.1+S5a.2+S5b+Impromptus A+B+C+S5c+S5d+S5e) | `7efd0a0` (S5e final closure) |
| DEF-158 | RESOLVED via Sprint 31.91 S3 (flatten-retry side-blindness fix) | `a11c001` |
| DEF-213 | RESOLVED via Sprint 31.91 (schema half S2b.1 + atomic-migration half S5a.1) | `S2b.1` + S5a.1 commits |
| DEF-214 | RESOLVED via Sprint 31.91 S5a.1 | S5a.1 commit |
| DEF-216 | RESOLVED via Sprint 31.91 impromptu hotfix | `c36a30c` |
| DEF-217 | RESOLVED via Sprint 31.91 Impromptu A (+ dual-layer regression at Impromptu B) | `e78a994` (+ `8efa72e`) |
| DEF-218 | RESOLVED via Sprint 31.91 Impromptu A | `e78a994` |
| DEF-219 | RESOLVED via Sprint 31.91 Impromptu A (AST regression guard) | `e78a994` |
| DEF-220 | RESOLVED via Sprint 31.91 Session 5c (Option A: REMOVAL of `acknowledgment_required_severities` field) | `3197472` |
| DEF-221 | RESOLVED via Sprint 31.91 Impromptu B (DatabentoHeartbeatEvent producer + suppression contract) | `8efa72e` |
| DEF-223 | RESOLVED via Sprint 31.91 Impromptu C (migration framework adoption across 7 separate DBs) | `3fefda8` |
| DEF-224 | RESOLVED via Sprint 31.91 Impromptu A (DDL deduplication) | `e78a994` |
| DEF-225 | RESOLVED via Sprint 31.91 Impromptu A (`ibkr_auth_failure` dedicated E2E test) | `e78a994` |

**5 NEW DEF entries to add** (use the routing language from `def-disposition-matrix.md` Section A):

- **DEF-226** — Full focus-trap on `AlertAcknowledgmentModal`. Source: S5d closeout J4. Status: OPEN — DEFERRED (LOW). Routing: future UI accessibility audit pass; bundle with S5d/S5e modal exit-animation INFO findings.
- **DEF-227** — Authenticated operator-id wiring into `AlertToastStack` and `AlertAcknowledgmentModal`. Source: S5d closeout J3. Status: BLOCKED on auth context infrastructure. Routing: first sprint introducing auth context / multi-operator login. When this lands, also closes the same-operator-two-tabs duplicate-ack edge case automatically.
- **DEF-228** — Backend `/api/v1/alerts/history` to grow `until` query parameter. Source: S5e closeout J3. Status: OPEN — DEFERRED (LOW). Routing: opportunistic — first future backend-alerts session. Currently `useAlertHistory` calls `/history?since=<from>` and applies `created_at_utc <= range.to` client-side filter; correct in interim, slightly wasteful on bandwidth.
- **DEF-229** — Observatory pagination virtualization for AlertsPanel when historical dataset is large. Source: S5e closeout. Status: OPEN — DEFERRED (LOW). Routing: opportunistic — observed slowness or operator complaint; suggested `@tanstack/react-virtual` on `AlertsTable` body.
- **DEF-230** — Audit-loading state and error-toast for `useAlertAuditTrail`. Source: S5e closeout. Status: OPEN — DEFERRED (LOW). Routing: opportunistic — operator complaint or production observability gap surfaces; thread `error` through hook return.

**6 pre-existing DEFs touched but UNCHANGED** (verify routing language remains current):

- DEF-208 (live-trading test fixture) — routes to live-enable transition sprint
- DEF-209 (Position.side persistence) — routes to Sprint 35+
- DEF-211 (D1+D2+D3 sprint-gating scope including RSK-DEC-386-DOCSTRING bound) — routes to Sprint 31.93
- DEF-212 (`_OCA_TYPE_BRACKET = 1` constant drift) — routes to Sprint 31.92
- DEF-215 (reconciliation per-cycle log spam) — DEFERRED with sharp revisit trigger
- DEF-222 (subscribe-before-rehydrate audit) — DEFERRED, bounded by first producer-wiring sprint introducing producer for `ReconciliationCompletedEvent`/`IBKRReconnectedEvent`/`DatabentoHeartbeatEvent`

**Other CLAUDE.md updates:**

- Update the "Current state" or equivalent section to reflect: Sprint 31.91 complete; 22 shadow variants still collecting CounterfactualTracker data; daily-flatten mitigation criterion #4 (sprint sealed) ✅ MET, criterion #5 pending (5 paper sessions clean post-seal).
- Update the most-cited foundational decisions list to include DEC-385 (Side-Aware Reconciliation Contract) and DEC-388 (Alert Observability Architecture) alongside DEC-386 which is already there.
- Update "Open DEF items of note" section: remove DEF-014 (RESOLVED); update remaining items per matrix.
- Verify the build track queue language is current: 1. Sprint 31B, 2. post-31.9 component ownership refactor (DEF-175 + sibling-class items per matrix), 3. Sprint 30, 4. Sprint 33, 5. Sprint 33.5, 6. Sprint 31.92 (DEF-212), 7. Sprint 31.93 (DEF-211 D1+D2+D3 + RSK-DEC-386-DOCSTRING bound), 8. post-31.9-reconnect-recovery (DEF-194/195/196 — likely first DEF-222 audit firing surface), 9. post-31.9-reconciliation-drift (potentially folded into 31.93 now that DEF-204 is mechanism-closed).

### File 2: `docs/decision-log.md`

**Add 2 new DEC entries.** Both are deferred-to-sprint-close per `pre-impromptu-doc-sync-manifest.md`. Use the materialization text from session closeouts as the source.

#### DEC-385 — Side-Aware Reconciliation Contract

**Source:** Session 2d closeout. Sprint: 31.91. Status: ACTIVE.

**Context:** Pre-Sprint-31.91, ARGUS reconciliation logic in OrderManager (Pass 1 startup, Pass 2 EOD) treated all unconfirmed positions identically regardless of broker-reported side. This was correct for ARGUS's long-only design assumption — but it meant phantom-short cascades (DEF-204) were "reconciled" by being treated as legitimate positions to track, perpetuating the cascade across daily reconciliation cycles.

**Decision:** Reconciliation operations are now side-aware. The 6-layer contract:

1. **Layer 1 (S2a):** main.py call-site builds typed dict from `broker.get_positions()` including side; reconciliation receives side as first-class field.
2. **Layer 2 (S2b.1):** `SystemAlertEvent.metadata` schema gains side field for forensic surface.
3. **Layer 3 (S2b.2):** OrderManager Pass 1 SELL detection + retry path threads side through.
4. **Layer 4 (S2c.1):** Phantom-short gate emits side-aware classifications and persists to `phantom_short_gated_symbols` SQLite table.
5. **Layer 5 (S2c.2):** EOD verify polling (Pass 2) treats SHORT-side positions as phantom-short candidates rather than long-position reconciliation targets.
6. **Layer 6 (S2d):** Audit-log enrichment via `phantom_short_override_audit` SQLite table records every operator override for forensic-grade replay.

**Consequence:** Reconciliation now correctly distinguishes ARGUS-managed long positions from broker-side anomalies. Combined with DEC-386 (OCA-Group Threading + Broker-Only Safety) which closes the upstream OCA mechanism, ~98% of DEF-204's cascade mechanism is now structurally closed. Operator's daily-flatten mitigation can cease after sprint-seal + 5 paper sessions clean.

**Cross-references:** DEC-386 (OCA architecture, complementary closure); DEF-204 (closed by mechanism); DEC-117 (atomic bracket orders, preserved byte-for-byte).

#### DEC-388 — Alert Observability Architecture

**Source:** Multi-session, deferred from Tier 3 #2 amended verdict 2026-04-28 per Pattern B. Sprint: 31.91 (S5a.1 + S5a.2 + S5b + Impromptus A+B+C + S5c + S5d + S5e). Status: ACTIVE.

**Context:** Pre-Sprint-31.91, ARGUS had no consumer-side architecture for the 11+ alert types emitted across HealthMonitor, OrderManager, IBKRBroker, and Databento data services. DEF-014 surfaced this in October 2025 as a structural gap — alerts were emitted via `SystemAlertEvent` but had no central consumer, no persistence, no UI surface. The system was operationally blind to its own alarms.

**Decision:** Multi-emitter consumer pattern with HealthMonitor as central consumer:

1. **Producer side (S5b + Impromptu B):** 15 emitter sites across HealthMonitor, OrderManager, IBKRBroker (`_reconnect()` end-of-retries → `ibkr_disconnect`; `_on_error()` CRITICAL non-connection else-branch → `ibkr_auth_failure`), and DatabentoDataService (`DatabentoHeartbeatEvent` with stale-suppression contract). All sites populate metadata.

2. **Consumer side (S5a.1):** HealthMonitor subscribes to `SystemAlertEvent` + 4 predicate handlers (`OrderFilledEvent`, `IBKRReconnectedEvent`, `DatabentoHeartbeatEvent`, `ReconciliationCompletedEvent`). Per-alert-type auto-resolution policy table (`POLICY_TABLE` in `alert_auto_resolution.py`) maps 13 alert types to predicate functions that determine when an alert can be auto-resolved.

3. **Storage (S5a.1 + S5a.2):** SQLite `data/operations.db` with 5 tables: `phantom_short_gated_symbols` (S2c.1), `phantom_short_override_audit` (S2d), `alert_acknowledgment_audit` (S5a.1; audit_kinds: ack/duplicate_ack/late_ack/auto_resolution), `alert_state` (S5a.2 + 3 indexes), `schema_version` (S5a.2; migration framework version tracking). The migration framework introduced at S5a.2 was extended at Impromptu C to all 8 ARGUS SQLite DBs.

4. **Restart recovery (S5a.2):** `rehydrate_alerts_from_db()` reconstructs `_alerts_active` map from `alert_state` rows on startup. Predicate handlers subscribed before rehydrate via `_subscribe_predicate_handlers()`. (Subscribe-before-rehydrate audit deferred as DEF-222 — bounded by first producer-wiring sprint introducing relevant producers.)

5. **REST API (S5a.1 + S5e RULE-007 scope expansion):** `GET /api/v1/alerts/active`, `GET /api/v1/alerts/history`, `POST /api/v1/alerts/{alert_id}/acknowledge` (atomic + idempotent: 200/404/200-late-ack); plus S5e-added `GET /api/v1/alerts/{alert_id}/audit` (audit trail per alert for Observatory detail view).

6. **WebSocket (S5a.1):** `/ws/v1/alerts` JWT-authenticated; emits `auth_success` → `snapshot` → 4 lifecycle deltas (`alert_active`, `alert_acknowledged`, `alert_auto_resolved`, `alert_archived` defensive forward-compat though no producer exists today).

7. **Frontend Layer 1 (S5c):** `useAlerts` TanStack-Query-plus-WebSocket-hybrid hook with reconnect-gated refetch via `wasDisconnectedRef`. `AlertBanner` component renders `severity === 'critical' && state === 'active'` only.

8. **Frontend Layer 2 (S5d):** `AlertToast` + `AlertToastStack` (queue cap at 5, oldest-dropped); `AlertAcknowledgmentModal` (reason ≥10 chars validated, role=dialog accessibility, duplicate-ack via `acknowledged_by` mismatch detection — backend returns 200 with original acknowledger preserved on idempotent path, no 409).

9. **Frontend Layer 3 (S5e):** `AlertsPanel` Observatory browsing surface (active + history tables, filters by severity/source/symbol, sortable, date-range picker default last-7-days UTC, `AlertDetailView` modal with metadata + audit trail). `AlertBanner` + `AlertToastStack` mounted at `AppShell.tsx` layout level for cross-page persistence (regression invariant 17 structurally pinned by `AppShell.alerts.test.tsx:163`). 5 in-Dashboard banner mounts + 5 in-Dashboard toast mounts removed.

**Severity policy:** Banner displays `critical` only; `warning`/`info` are toast-only. Per-alert-type `PolicyEntry.operator_ack_required` is canonical home for severity-based gating (replaced removed `AlertsConfig.acknowledgment_required_severities` field per DEF-220 Option A REMOVAL).

**Consequence:** DEF-014 FULLY RESOLVED. ARGUS now has end-to-end alert observability from emit through operator acknowledgment with audit trail. The Observatory's `/observatory/alerts` toggle overlay provides historical browsing; the cross-page banner ensures critical alerts cannot be missed regardless of which Command Center page is active.

**Cross-references:** DEF-014 (closed), DEF-217/218/219/220/221/223/224/225 (Tier 3 #2 spawned, all closed); DEF-222 (deferred to first producer-wiring sprint); DEC-386 (parallel architectural closure for DEF-204); DEC-385 (parallel architectural closure for reconciliation drift); DEC-345 (separate-DB pattern for operations.db); DEC-328 (test discipline; lesson learned at post-S5e catalog hotfix — surfaced as F.1 in process-evolution.md).

### File 3: `docs/dec-index.md`

**Add 2 new entries** matching the file's existing index format. Both are ACTIVE status with sprint attribution to 31.91.

- **DEC-385** — Side-Aware Reconciliation Contract (S2d). Status: ACTIVE. Cross-references DEC-386 (parallel closure for DEF-204).
- **DEC-388** — Alert Observability Architecture (multi-session, sprint 31.91 sprint-close materialization). Status: ACTIVE. Cross-references DEF-014 (closed), DEC-386 (parallel architectural closure pattern), DEC-345 (separate-DB pattern).

DEC-386 is already in the index (Tier 3 #1 verdict 2026-04-27). Verify it remains correctly attributed and ACTIVE.

### File 4: `docs/architecture.md`

**Major addition: §14 — Alert Observability Subsystem**

Add a new section that documents the alert observability architecture as the canonical reference pattern for future emitters. Use DEC-388's text above as source material; structure the section as:

- §14.1 Overview (multi-emitter consumer pattern, HealthMonitor as central consumer)
- §14.2 Producer pattern (15 emitter sites; `SystemAlertEvent.metadata` schema; stale-suppression contract examples)
- §14.3 Consumer pattern (HealthMonitor subscriptions; `POLICY_TABLE`; predicate functions; auto-resolution flow)
- §14.4 Storage layer (`data/operations.db` 5 tables; migration framework; rehydrate-on-startup)
- §14.5 REST + WebSocket interfaces (4 REST endpoints; 6 WS message types; JWT auth)
- §14.6 Frontend integration (`useAlerts` hook; `AlertBanner` + `AlertToastStack` + `AlertAcknowledgmentModal` + `AlertsPanel` + `AlertDetailView`; severity policy)
- §14.7 Reference materials (DEC-388, DEF-014 closure, sprint 31.91 closeout files)

**Verify other sections:**

- **§3.7 (Order Manager):** Verify side-aware reconciliation per DEC-385 is documented. Cross-reference Layers 1-6 from S2a/S2b.1/S2b.2/S2c.1/S2c.2/S2d.
- **§3.7 (Order Manager) — Retry path side-check:** Add subsection covering S3's flatten-retry side-blindness fix (DEF-158 RESOLVED).
- **§3.3 (Broker Abstraction) — OCA architecture:** Verify DEC-386 OCA-Group Threading is documented (Tier 3 #1 may already have written this; verify and amend if needed).
- **§3.5 or §15 — Validation infrastructure:** Add S4's falsifiable validation gate documentation (mass-balance script `scripts/validate_session_oca_mass_balance.py`; symbol-level audit; integration markers).
- **§3.8 or new subsection — Migration framework:** Document the migration framework introduced at S5a.2 + extended to all 8 SQLite DBs at Impromptu C. Each per-DB module follows the `argus/data/migrations/operations.py` template; `apply_migrations()` called in each owning service's `initialize()` method; `schema_version` table tracks migration versions.

**API catalog:** Already up-to-date per catalog hotfix `4c737d5`. Verify no further drift via:

```bash
python scripts/generate_api_catalog.py --verify
```

If this returns non-OK, regenerate via:

```bash
python scripts/generate_api_catalog.py --path-prefix /api/v1/<thing>
```

and paste the output into the relevant section.

### File 5: `docs/risk-register.md`

**Add 1 new RSK entry:**

- **RSK-DEC-386-DOCSTRING** — `OrderManager.reconstruct_from_broker()` STARTUP-ONLY contract is currently documented in docstring only; no runtime gate prevents accidental mid-session invocation. Source: Tier 3 #1 disposition. Bound: Sprint 31.93 DEF-211 D1 will convert the contract from docstring to runtime gate. Risk severity: LOW (current callers are all startup-context; no observed mid-session invocation paths exist). Mitigation: docstring is read by reviewers; sprint-31.91 closeout pattern reinforced explicit STARTUP-ONLY language in all impl prompts touching the function.

### File 6: `docs/roadmap.md`

**Updates:**

- Mark Sprint 31.91 ✅ COMPLETE in the sprint-history annotation.
- Update the build track queue's "next 5 sprints" priority list:
  1. Sprint 31B (Research Console / Variant Factory) — unchanged
  2. **post-31.9-component-ownership** (DEF-175/182/193/201/202 + 3 sibling-class items absorbed: Impromptu B Concern 2, Impromptu C LOW #1, S2c.1 OrderManager.stop()) — explicit absorption per `def-disposition-matrix.md`
  3. **Sprint 31.92** — DEF-212 (`_OCA_TYPE_BRACKET = 1` constant drift fix per Tier 3 #1 disposition)
  4. **Sprint 31.93** — DEF-211 D1+D2+D3 scope including RSK-DEC-386-DOCSTRING bound (D1: convert STARTUP-ONLY contract to runtime gate; D2: boot-time reconciliation policy + IMPROMPTU-04 gate refinement; D3: `max_concurrent_positions` broker-only-longs accounting fix)
  5. **post-31.9-reconnect-recovery** (DEF-194/195/196) — likely first surface for DEF-222 subscribe-before-rehydrate audit firing
  6. Sprint 30 (Short Selling) — deferred until longs profitable; unchanged
  7. Sprint 33 (Statistical Validation) — applied to shadow-proven configs; unchanged
  8. Sprint 33.5 (Adversarial Stress Testing) — unchanged

- Update "Current state" section: 22 shadow variants still collecting CounterfactualTracker data; DEF-204 mechanism architecturally CLOSED; DEF-014 alert observability gap CLOSED; daily-flatten mitigation criterion #4 (sprint sealed) ✅ MET as of D14, criterion #5 pending.

### File 7: `docs/sprint-history.md`

**Add full Sprint 31.91 entry** using the Sprint Summary Narrative above (or adapt to match the file's existing per-sprint section style — typically a header + summary table + per-session bullets + key DECs callout + carry-forward routing).

The 25 implementation sessions + 2 in-sprint hotfixes should each get at minimum a bulleted entry; the Tier 3 reviews + their dispositions should be called out as architectural milestones; the in-sprint hotfixes (`c36a30c` DEF-216 + `4c737d5` catalog freshness) should be noted with their hotfix nature explicit.

If the file uses a sprint-summary table format like the one in `docs/project-knowledge.md`, append a row:

| Sprint | Name | Tests | Date | Key DECs |
|---|---|---|---|---|
| 31.91 | Reconciliation Drift / Phantom-Short Fix + Alert Observability Completion | 5269+913V | Apr 22-28 | DEC-385, DEC-388 (DEC-386 from Tier 3 #1) |

### File 8: `docs/sprint-campaign.md`

**Mark Sprint 31.91 complete** in whatever the file's tracking format is. Verify the next sprint(s) on the campaign list match the updated build track queue from roadmap.md.

### File 9: `docs/project-knowledge.md`

**Updates:**

- Sprint history table: append Sprint 31.91 row matching the format shown above.
- "Sprints completed" count: increment to include 31.91.
- "Active sprint" → "None — between sprints. Sprint 31.91 sealed at D14 doc-sync."
- "Open DEF items of note": remove DEF-014 (RESOLVED); update remaining items per `def-disposition-matrix.md`. Add DEF-222 (subscribe-before-rehydrate audit, opportunistic per matrix); add DEF-226/227/228/229/230 with one-line summaries.
- "Current build track" section: update to reflect roadmap.md changes.
- Test count baseline: refresh to 5,269 pytest + 913 Vitest.
- "Three-tier system" section: verify §14 alert observability subsystem cross-reference is added.
- "Active strategies" table: no changes (sprint did not modify strategies).

### File 10: `docs/project-bible.md`

**Verify only.** Sprint 31.91 should not have changed the project's foundational what-and-why; verify no drift has accumulated. If the bible references DEF-014 as an open gap or describes ARGUS as "blind to its own alarms," update those passages to reflect closure.

### File 11: `docs/process-evolution.md`

**Add 4 new entries (F.1 through F.4) per `def-disposition-matrix.md` Section F:**

#### F.1 — DEC-328 full-suite-at-Tier-1 process gap

**Surfaced by:** Post-S5e catalog freshness hotfix (`4c737d5`).

**Observation:** S5e Tier 2 reviewer + S5e closeout both reported scoped tests (`test_alerts.py 12→15` + Vitest `902→913`) without running full pytest. The catalog freshness gate (`tests/docs/test_architecture_api_catalog_freshness.py`, DEF-168 regression guard) only fires on full suite, so the missing audit endpoint in `docs/architecture.md` slipped through to CI. DEC-328 mandates "full suite at sprint entry, each close-out, and final review" — scoped-only at Tier 1 boundary (S5e closeout) was the gap.

**Resolution path:**

- Tighten DEC-328 with explicit "full suite required at Tier 1 boundary" language in next sprint planning conversation.
- OR add a CI-side guard that fires on PR boundaries regardless of session-local test scope.
- OR amend `templates/work-journal-closeout.md` to require explicit declaration of "full suite verified" vs "scoped only" with mandatory full-suite-required at sprint-final-session boundary.

**Carry-forward target:** Next sprint planning conversation (Sprint 31.92 likely).

#### F.2 — RULE-038 drift surface area (already addressed)

**Surfaced by:** Sprint 31.91's RULE-038 drift counts ranged from 2 (S5b: 2 stale line numbers) to 7 (S5d: 7 prompt-vs-current-code drifts). S2b.2's spec line range `:1670-1750` for `order_manager.py` didn't contain the claimed SELL-detection branching; S5d's drifts included `frontend/src/` vs `argus/ui/src/`, `Layout.tsx` vs `AppShell.tsx`, hook contract drifts; S5e's drifts included `Layout.tsx` vs `AppShell.tsx` again, `/audit` endpoint pre-existence (triggered halt-and-fix), DEF numbering collisions.

**Resolution:** Already addressed in workflow metarepo at `templates/implementation-prompt.md` v1.5.0 (structural-anchor amendment 2026-04-28). Ongoing reinforcement in next sprint planning recommended.

#### F.3 — Per-session register discipline (pattern working)

**Observation:** The per-session register discipline formalized at S2a (workflow v1.2.0) held firm through 18 register refreshes covering 25 implementation sessions + 2 in-sprint hotfixes. Zero conversation drift across the entire sprint despite accumulated context from multiple Tier 3 reviews + amended verdicts + 9 mid-sprint DEF assignments.

**Carry-forward:** N/A — pattern is working; document as positive case study in process-evolution.md for future sprint-planning reference.

#### F.4 — Bookkeeping discipline (8 consecutive sessions clean)

**Observation:** S5a.2 + S5b + Impromptu A + Impromptu B + S5c + Impromptu C + S5d + S5e closeouts cited `tests_added` matching actual delta. S5a.1's +21 vs +18 cosmetic discrepancy was a one-off; RULE-038 sub-bullet feedback was internalized cleanly across the trailing 8 sessions.

**Carry-forward:** N/A — pattern is working; document as positive reinforcement.

### File 12: `docs/pre-live-transition-checklist.md`

**Verify items from S4 are recorded:**

- S4 Phase 5a items (any pre-live config/test values that need restoration before live)
- S4 mass-balance validation infrastructure (`scripts/validate_session_oca_mass_balance.py`) cross-reference
- DEC-386 broker-only safety net behavior expectations under live trading
- DEC-385 side-aware reconciliation behavior under live trading

If the file does not yet reference these, add them per S4 closeout content.

### File 13: `docs/protocols/market-session-debrief.md`

**Verify Phase 7.4 slippage-related additions from S4 are recorded** (if S4 amended this protocol).

### File 14: `docs/operations/parquet-cache-layout.md`

**Verify only.** Sprint 31.91 did not modify the parquet cache layout; this file should remain unchanged. Cross-check that DEC-385 / DEC-388 narrative doesn't inadvertently reference parquet cache concerns.

### Files 15+: Other documentation files

Run a comprehensive scan:

```bash
ls docs/
ls docs/strategies/
ls docs/architecture/
ls docs/protocols/
ls docs/operations/
```

For any file that mentions DEF-014, DEF-204, alert observability, reconciliation drift, OCA threading, or anything Sprint-31.91-touched, verify the language is consistent with the post-sprint state. Common refresh targets:

- DEF-204 references: should now read "RESOLVED via DEC-386 (Tier 3 #1) + DEC-385 (S2d) + S3 + S4" (mechanism architecturally closed; daily-flatten mitigation criterion #4 met)
- DEF-014 references: should now read "RESOLVED via Sprint 31.91 (full alert observability pipeline)"
- Alert observability descriptions: should reference DEC-388 + architecture.md §14 as canonical
- "Long-only by design" references: still accurate per DEC-166; DEC-385 and DEC-386 reinforce rather than supersede this

---

## Embedded Close-Out Content

> Per `templates/work-journal-closeout.md` v1.4.0 human-in-the-loop guidance: this section embeds the Work Journal close-out data directly. The structured truth is in `work-journal-register.md`; this is the framing summary.

### DEF Numbers Assigned During Sprint 31.91

| DEF # | Description | Status | Source |
|---|---|---|---|
| DEF-217 | Tier 3 #2 Concern A: alert dedup string match | ✅ RESOLVED via Impromptu A (`e78a994`) + dual-layer regression at Impromptu B (`8efa72e`) | Tier 3 #2 |
| DEF-218 | Tier 3 #2 Concern D: AST regression guard for emitter metadata | ✅ RESOLVED via Impromptu A (`e78a994`) | Tier 3 #2 |
| DEF-219 | Tier 3 #2 Concern B: AST regression guard | ✅ RESOLVED via Impromptu A (`e78a994`) | Tier 3 #2 |
| DEF-220 | Tier 3 #2 Concern C: `acknowledgment_required_severities` consumer wiring | ✅ RESOLVED via Session 5c — Option A REMOVAL (`3197472`) | Tier 3 #2 |
| DEF-221 | Tier 3 #2 Concern F: `DatabentoHeartbeatEvent` producer | ✅ RESOLVED via Impromptu B (`8efa72e`) | Tier 3 #2 |
| DEF-222 | Tier 3 #2 Item 2: subscribe-before-rehydrate audit | OPEN — DEFERRED (bounded by first producer-wiring sprint) | Tier 3 #2 |
| DEF-223 | Tier 3 #2 Item 8: migration framework adoption sweep | ✅ RESOLVED via Impromptu C (`3fefda8`) | Tier 3 #2 |
| DEF-224 | Tier 3 #2 Concern E: DDL deduplication | ✅ RESOLVED via Impromptu A (`e78a994`) | Tier 3 #2 |
| DEF-225 | Tier 3 #2 Item 1: `ibkr_auth_failure` dedicated E2E test | ✅ RESOLVED via Impromptu A (`e78a994`) | Tier 3 #2 |
| DEF-226 | Full focus-trap on `AlertAcknowledgmentModal` | OPEN — DEFERRED (LOW; future UI accessibility audit) | S5d closeout J4 |
| DEF-227 | Authenticated operator-id wiring into Toast/Modal | OPEN — DEFERRED (LOW; BLOCKED on auth context) | S5d closeout J3 |
| DEF-228 | Backend `/api/v1/alerts/history` `until` query parameter | OPEN — DEFERRED (LOW; opportunistic) | S5e closeout J3 |
| DEF-229 | Observatory pagination virtualization for `AlertsPanel` | OPEN — DEFERRED (LOW; opportunistic) | S5e closeout |
| DEF-230 | Audit-loading state and error-toast for `useAlertAuditTrail` | OPEN — DEFERRED (LOW; opportunistic) | S5e closeout |

**14 DEFs assigned during sprint** (9 from Tier 3 #2 + 5 from S5d/S5e). 8 of 9 Tier-3-#2-spawned DEFs RESOLVED-IN-SPRINT; 1 deferred (DEF-222). All 5 S5d/S5e DEFs deferred (LOW priority opportunistic with clear triggers).

### Pre-Existing DEFs Resolved During Sprint 31.91

| DEF # | Description | Resolution |
|---|---|---|
| DEF-014 | Alert observability gap (PRIMARY DEFECT, October 2025) | ✅ FULLY RESOLVED via S5a.1+S5a.2+S5b+Impromptus A+B+C+S5c+S5d+S5e (`7efd0a0` final closure) |
| DEF-158 | Flatten retry side-blindness | ✅ RESOLVED via Session 3 (`a11c001`) |
| DEF-213 | `SystemAlertEvent.metadata` schema gap | ✅ RESOLVED via S2b.1 (schema half) + S5a.1 (atomic-migration half) |
| DEF-214 | EOD verify polling | ✅ RESOLVED via S5a.1 |
| DEF-216 | `test_get_regime_summary` ET-midnight rollover race | ✅ RESOLVED via in-sprint hotfix (`c36a30c`) |

**5 pre-existing DEFs RESOLVED in-sprint.** Combined with the 9 in-sprint-assigned DEFs that were also resolved, **13 total DEFs RESOLVED-IN-SPRINT**.

### DEC Numbers Tracked During Sprint 31.91

| DEC # | Description | Session |
|---|---|---|
| DEC-385 | Side-Aware Reconciliation Contract (6-layer) | S2d (materialized at sprint-close per Pattern B) |
| DEC-386 | OCA-Group Threading + Broker-Only Safety (4-layer) | Tier 3 #1 verdict 2026-04-27 (already in decision-log.md) |
| DEC-388 | Alert Observability Architecture (multi-emitter consumer pattern) | Multi-session, deferred from Tier 3 #2 amended verdict 2026-04-28 per Pattern B (materialized at sprint-close) |

**3 DECs entered.** DEC-386 is already materialized in decision-log.md from Tier 3 #1; DEC-385 + DEC-388 require materialization at this D14.

### Resolved Items (do NOT create new DEF entries for these)

These items were identified as carry-forwards but resolved within the sprint. Do NOT create DEF entries:

| Item | Resolution | Session |
|---|---|---|
| DEF-014 producer side (IBKR emitter TODOs) | 2 emitters wired at S5b | S5b |
| DEF-014 consumer side (HealthMonitor subscribe + storage + REST + WS) | S5a.1 + S5a.2 | S5a.1 + S5a.2 |
| DEF-014 frontend Layer 1 (banner + hook) | `useAlerts` hook + `AlertBanner` mount on Dashboard | S5c |
| DEF-014 frontend Layer 2 (toast + ack-error modal) | `AlertToast` + `AlertToastStack` + `AlertAcknowledgmentModal` | S5d |
| DEF-014 frontend Layer 3 (Observatory + cross-page) | `AlertsPanel` + `AppShell.tsx` cross-page mount + `/audit` endpoint | S5e |
| DEF-204 mechanism (phantom-short cascade root cause) | DEC-386 OCA architecture (Tier 3 #1) + DEC-385 side-aware reconciliation (S2d) + S3 retry side-check + S4 falsifiable validation | Multi-session |
| Migration framework foundational adoption | `argus/data/migrations/` framework + operations.db v1 | S5a.2 |
| Migration framework universal adoption | All 8 ARGUS SQLite DBs framework-managed | Impromptu C |
| OCA-group identifier threading through bracket-order placement | 4-layer DEC-386 implementation | S0+S1a+S1b+S1c (pre-Tier-3-#1) |
| Side-aware reconciliation contract | 6-layer DEC-385 implementation | S2a+S2b.1+S2b.2+S2c.1+S2c.2+S2d |
| 5 in-Dashboard `AlertBanner` mounts removed | Relocated to `AppShell.tsx` at S5e | S5e (was S5c carry-forward) |
| 5 in-Dashboard `AlertToastStack` mounts removed | Relocated to `AppShell.tsx` at S5e | S5e (was S5d carry-forward) |
| `_AUDIT_DDL` duplicate in `argus/api/routes/alerts.py` | Deleted at Impromptu A | Impromptu A (was S5a.2 reviewer F2) |
| `ibkr_auth_failure` E2E coverage gap | `TestE2EIBKRAuthFailureAutoResolution` added at Impromptu A | Impromptu A (was S5b reviewer F2) |
| API catalog freshness for `/api/v1/alerts/{alert_id}/audit` | Catalog regenerated post-S5e | Catalog hotfix `4c737d5` |

### Outstanding Code-Level Items (NOT DEF-worthy)

See `def-disposition-matrix.md` Sections C + D for the complete list with confidence-graded routing. Headlines:

- 3 sibling-class items routed to `post-31.9-component-ownership` (Impromptu B Concern 2, Impromptu C LOW #1, S2c.1 OrderManager.stop())
- 2 items routed to Sprint 31.5 (31.75 SQL f-string + view-name coupling — sweep tooling)
- 16 OPPORTUNISTIC items (cosmetic / event-driven / nice-to-have)
- 2 modal exit-animation INFO observations (S5d INFO-1 + S5e INFO-1) — recommended bundle with DEF-226 future UI polish session

### Corrections Needed in Initial Doc-Sync Patch

**None.** Work Journal handoff is included directly in this prompt; no separate close-out artifact precedes this D14 doc-sync.

### Mid-sprint doc-syncs in this sprint

- **Pre-impromptu doc-sync** (2026-04-22, manifest at `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md`, commit `948b978`):
  - 13 DEF transitions claimed → all 13 to be APPLIED at this D14
  - 2 DEC deferrals (DEC-385 + DEC-388) → both to be MATERIALIZED at this D14

No further mid-syncs occurred. Tier 3 #2's amended verdict on 2026-04-28 deferred DEC-388 materialization to sprint-close (Pattern B per `protocols/mid-sprint-doc-sync.md` v1.0.0) rather than firing a new mid-sync.

---

## Verification Steps

After applying all changes, run the following verification suite:

### 1. Full pytest suite

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q
```

Expected: **5269 passed, 0 failed** (with documented pre-existing flakes possibly producing warnings — DEF-150 / DEF-167 / DEF-171 / DEF-190 / DEF-192 family). Any test that fails post-doc-sync is a regression and must be investigated before commit.

If `tests/test_main.py` is being run separately:

```bash
python -m pytest tests/test_main.py -q
```

Expected: **39 pass / 5 skip** unchanged.

### 2. Vitest suite

```bash
cd argus/ui && npx vitest run
```

Expected: **913 passed** unchanged. (Doc-sync changes nothing in `argus/ui/`; this is a smoke test.)

### 3. API catalog freshness

```bash
python scripts/generate_api_catalog.py --verify
```

Expected: `OK — architecture.md lists every REST + WebSocket endpoint.`

### 4. DEF index integrity

After all CLAUDE.md edits, verify no DEF appears as both OPEN and RESOLVED in the file:

```bash
grep -c "DEF-014.*OPEN\|DEF-014.*RESOLVED" CLAUDE.md
```

Each resolved DEF should show RESOLVED exactly once and OPEN zero times.

### 5. DEC-index integrity

```bash
grep -c "DEC-385\|DEC-388" docs/dec-index.md
```

Both DEC-385 and DEC-388 should appear exactly once each.

### 6. Sprint history append

```bash
grep "31.91" docs/sprint-history.md | head -5
```

Should show the new Sprint 31.91 entry with appropriate context.

### 7. Cross-reference sanity

```bash
grep -rn "DEF-014" docs/ | grep -v "RESOLVED\|sprint-31.91"
```

Should return zero matches (any remaining references should mark DEF-014 as resolved or be in sprint-31.91 historical artifacts).

---

## Commit Message Guidance

Use a single comprehensive commit at the end of the doc-sync. Suggested message:

```
docs(sprint-31.91): D14 doc-sync — sprint close-out (DEF-014 + DEF-204 mechanism FULLY RESOLVED; DEC-385 + DEC-388 materialized; 13 DEF transitions applied)

Sprint 31.91 sealed. Comprehensive documentation refresh covering:

- CLAUDE.md: 13 DEF transitions applied (DEF-014 + DEF-158 + DEF-213
  + DEF-214 + DEF-216 + DEF-217 + DEF-218 + DEF-219 + DEF-220 +
  DEF-221 + DEF-223 + DEF-224 + DEF-225 RESOLVED-IN-SPRINT); 5 new
  DEFs added (DEF-226/227/228/229/230); test count baseline refreshed
  (5,080 → 5,269 pytest; 866 → 913 Vitest); build track queue
  updated.
- decision-log.md: DEC-385 (Side-Aware Reconciliation Contract,
  6-layer) + DEC-388 (Alert Observability Architecture, multi-emitter
  consumer pattern) materialized from sprint-close-deferred state per
  pre-impromptu-doc-sync-manifest.md.
- dec-index.md: DEC-385 + DEC-388 entries added; DEC-386 (already
  materialized at Tier 3 #1) verified.
- architecture.md: §14 alert observability subsystem added (canonical
  reference for future emitters); §3.7 amended for DEC-385 side-aware
  reconciliation + S3 retry-path side-check; §3.3 verified for
  DEC-386 OCA architecture; new validation infrastructure subsection
  for S4; migration framework subsection for S5a.2 + Impromptu C
  expansion to all 8 SQLite DBs. API catalog already current per
  catalog hotfix 4c737d5.
- risk-register.md: RSK-DEC-386-DOCSTRING added (bounded by Sprint
  31.93 DEF-211 D1).
- roadmap.md: Sprint 31.91 marked complete; build track queue
  re-prioritized with explicit absorption of 3 sibling-class items
  into post-31.9-component-ownership; Sprint 31.92 + 31.93
  positioned.
- sprint-history.md: full Sprint 31.91 entry added (25 implementation
  sessions + 2 Tier 3 reviews + 2 in-sprint hotfixes).
- sprint-campaign.md: Sprint 31.91 marked complete.
- project-knowledge.md: sprint history table updated; Open DEF items
  refreshed; build track queue updated.
- project-bible.md: verified (no drift).
- process-evolution.md: F.1 (DEC-328 full-suite-at-Tier-1 gap from
  catalog hotfix lesson) + F.2 (RULE-038 drift surface area, already
  addressed) + F.3 (per-session register discipline, 18 refreshes) +
  F.4 (bookkeeping discipline, 8 consecutive sessions clean) added.
- pre-live-transition-checklist.md: S4 items verified.
- protocols/market-session-debrief.md: S4 amendments verified.

Sprint 31.91 outcome:
- DEF-014 (PRIMARY DEFECT, October 2025): FULLY RESOLVED via full
  alert observability pipeline.
- DEF-204 mechanism (phantom-short cascade): architecturally CLOSED
  via DEC-386 (4 layers) + DEC-385 (6 layers) + S3 retry side-check
  + S4 falsifiable validation. Daily-flatten mitigation criterion #4
  (sprint sealed) MET; criterion #5 (5 paper sessions clean) pending.
- 8 of 9 Tier-3-#2-spawned DEFs RESOLVED-IN-SPRINT; DEF-222 alone
  deferred (subscribe-before-rehydrate audit, bounded by first
  producer-wiring sprint).
- Migration framework spans all 8 ARGUS SQLite DBs (Impromptu C
  sprint-spec D16 fulfilled).
- 5 new opportunistic DEFs (DEF-226/227/228/229/230) filed with clear
  triggers.
- Sprint-wide observation: DEC-328 full-suite-at-Tier-1 process
  discipline gap surfaced via post-S5e catalog hotfix; documented in
  process-evolution.md F.1 for next sprint planning.

Process discipline metrics:
- 18 work-journal-register refreshes absorbed without conversation
  drift.
- 8 consecutive sessions with closeout tests_added matching actual
  delta.
- 6 main.py scoped exceptions documented (all backend-layer;
  finalized at S5a.2).
- RULE-038 drift counts ranged 2-7 per session, all reviewer-verified
  immaterial; already addressed in templates/implementation-prompt.md
  v1.5.0.

Anchor commit at sprint-close: 4c737d5.
DEF disposition matrix: docs/sprints/sprint-31.91-reconciliation-drift/def-disposition-matrix.md
Work journal register: docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md

Cross-references: DEC-385, DEC-386, DEC-388 (decision-log.md);
DEF-014, DEF-158, DEF-213, DEF-214, DEF-216, DEF-217 through DEF-225
(CLAUDE.md transitions); DEF-226 through DEF-230 (new opportunistic
LOW deferrals); RSK-DEC-386-DOCSTRING (risk-register.md); F.1-F.4
(process-evolution.md).

Closes Sprint 31.91.
```

---

## Final Pre-Push Checklist

Before `git push origin main`, verify:

- [ ] All 13 RESOLVED-IN-SPRINT DEF transitions applied to CLAUDE.md (no DEF appears as both OPEN and RESOLVED)
- [ ] All 5 new DEF entries (DEF-226/227/228/229/230) added to CLAUDE.md
- [ ] DEC-385 + DEC-388 written to decision-log.md (full entries with cross-references)
- [ ] DEC-385 + DEC-388 added to dec-index.md
- [ ] architecture.md §14 alert observability subsystem added
- [ ] architecture.md §3.x amendments for DEC-385/DEC-386/S3/S4/migration framework verified
- [ ] risk-register.md RSK-DEC-386-DOCSTRING added
- [ ] roadmap.md updated (Sprint 31.91 complete; build track queue re-prioritized)
- [ ] sprint-history.md Sprint 31.91 entry added (full prose + per-session bullets)
- [ ] sprint-campaign.md marks Sprint 31.91 complete
- [ ] project-knowledge.md sprint history table appended; Open DEF items refreshed
- [ ] project-bible.md verified (no DEF-014 "open gap" language remaining)
- [ ] process-evolution.md F.1 + F.2 + F.3 + F.4 added
- [ ] pre-live-transition-checklist.md S4 items verified
- [ ] CLAUDE.md test count baseline: 5,080 → 5,269 pytest; 866 → 913 Vitest
- [ ] Full pytest suite passes (5269 / 0 failed)
- [ ] Vitest suite passes (913 / 0 failed)
- [ ] `python scripts/generate_api_catalog.py --verify` returns OK
- [ ] No source code, test, or config files modified (this is a docs-only sync)
- [ ] Single comprehensive commit with the suggested message above
- [ ] Sprint 31.91 is sealed; daily-flatten mitigation criterion #4 (sprint sealed) ✅ MET

---

## Reference Material List

The Claude Code session executing this prompt should have read access to:

### Sprint folder canonical artifacts (READ FIRST)

- `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md` (commit `948b978`) — mid-sprint manifest
- `docs/sprints/sprint-31.91-reconciliation-drift/def-disposition-matrix.md` — D14 routing reference
- `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md` — structured truth (post-Session-5e + post-catalog-hotfix)

### Tier 3 review verdicts

- `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md`
- `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md`

### All 25 session closeouts + 25 reviews

```
session-0-closeout.md + session-0-review.md
session-1a-closeout.md + session-1a-review.md
session-1b-closeout.md + session-1b-review.md
session-1c-closeout.md + session-1c-review.md
session-2a-closeout.md + session-2a-review.md
session-2b.1-closeout.md + session-2b.1-review.md
session-2b.2-closeout.md + session-2b.2-review.md
session-2c.1-closeout.md + session-2c.1-review.md
session-2c.2-closeout.md + session-2c.2-review.md
session-2d-closeout.md + session-2d-review.md
session-3-closeout.md + session-3-review.md
session-4-closeout.md + session-4-review.md
session-5a.1-closeout.md + session-5a.1-review.md
session-5a.2-closeout.md + session-5a.2-review.md
session-5b-closeout.md + session-5b-review.md
session-5c-closeout.md + session-5c-review.md
session-5d-closeout.md + session-5d-review.md
session-5e-closeout.md + session-5e-review.md
impromptu-a-closeout.md + impromptu-a-review.md
impromptu-b-closeout.md + impromptu-b-review.md
impromptu-c-closeout.md + impromptu-c-review.md
```

### In-sprint hotfix references

- `c36a30c` (DEF-216 ET-midnight rollover hotfix between S2c.2 and S2d) — annotated in session-2c.2-closeout.md
- `4c737d5` (post-S5e API catalog freshness regeneration) — annotated in work-journal-register.md

### Sprint planning artifacts (for narrative context)

- `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md`
- `docs/sprints/sprint-31.91-reconciliation-drift/design-summary.md`
- `docs/sprints/sprint-31.91-reconciliation-drift/spec-by-contradiction.md`
- `docs/sprints/sprint-31.91-reconciliation-drift/escalation-criteria.md`
- `docs/sprints/sprint-31.91-reconciliation-drift/regression-checklist.md`
- `docs/sprints/sprint-31.91-reconciliation-drift/doc-update-checklist.md`

### Workflow metarepo references

- `~/workflow/protocols/mid-sprint-doc-sync.md` v1.0.0 (manifest interpretation)
- `~/workflow/templates/work-journal-closeout.md` v1.4.0 (close-out structure)
- `~/workflow/templates/doc-sync-automation-prompt.md` v1.2.0 (this prompt's template)
- `~/workflow/protocols/sprint-planning.md` v1.2.0 (sprint methodology context)

---

## Closing Notes

This is the final D14 doc-sync for Sprint 31.91. The sprint accomplished both primary defect resolutions (DEF-014 alert observability + DEF-204 phantom-short mechanism), shipped 2 architectural decisions (DEC-385 + DEC-388), processed 9 Tier-3-spawned DEFs (8 RESOLVED-IN-SPRINT + 1 deferred), filed 5 new opportunistic DEFs with clear routing, and adopted the migration framework universally across all 8 ARGUS SQLite DBs.

The sprint folder's `def-disposition-matrix.md` is the canonical carry-forward routing reference. Future sprints picking up DEF-211 (Sprint 31.93), DEF-212 (Sprint 31.92), DEF-209 (Sprint 35+), DEF-208 (live-enable), DEF-222 (first producer-wiring sprint), and the sibling-class items absorbed by `post-31.9-component-ownership` should consult the matrix for routing language.

Daily-flatten mitigation criterion #4 (sprint sealed) is MET upon successful execution of this D14 doc-sync. Criterion #5 (5 paper sessions clean post-seal) becomes the next observable gate; cessation of the daily mitigation pattern can be evaluated thereafter.

Sprint 31.91 closes here.

---

*End Sprint 31.91 D14 Doc-Sync Prompt.*
