# Sprint 31.91 Design Summary (REVISED 3rd pass — 18-session shape)

> **Compaction-insurance artifact** — produced during Phase B of sprint
> planning, revised after Phase C-1 first-pass adversarial review (revisions
> resolved 7 BLOCKING/HIGH), revised again after Phase C-1 second-pass
> review (revisions resolved 5 BLOCKING + 4 HIGH + 6 MEDIUM + 3 LOW per
> Phase A revisit findings), and revised a **third time** after Phase C-1
> third-pass review (Conditional CLEAR — revisions resolve 5 HIGH + select
> MEDIUM/LOW; remaining MEDIUM/LOW captured in `PHASE-D-OPEN-ITEMS.md`).
> If conversation context is lost, this document alone is sufficient to
> regenerate the full sprint package.

**Sprint ID:** `sprint-31.91-reconciliation-drift`
**Predecessor:** Sprint 31.9 (Health & Hardening campaign-close, sealed 2026-04-24)
**Planning date:** 2026-04-27 (revised 2026-04-27 PM after Phase A revisit)
**Execution mode:** Human-in-the-loop (no runner config)
**Branch strategy:** Work directly on `main` (operator-elected; paper trading runs on `main` daily)

## Sprint Goal (revised, 2nd pass)

Eliminate DEF-204's upstream cascade of unintended short positions across
**all known surfaces** AND deliver complete alert-observability so the
operator can see safety-critical events in real-time during paper trading
and live operation. Specifically:

- Close the bracket-children OCA-race + standalone-SELL no-OCA mechanism
  across all 5 SELL placement paths
- Close the broker-only-position OCA orphan window with
  `cancel_all_orders(symbol, await_propagation=True)` before SELL
- Close the side-blind reconciliation contract with typed
  `ReconciliationPosition`
- Close the side-blind RISK MANAGER position cap, EOD Pass 2 short
  detection, and Health integrity check (the three-site B5 pattern)
- Apply IMPROMPTU-04's 3-branch pattern to the DEF-158 retry path
- Make phantom-short detection observable via `SystemAlertEvent` and
  recoverable via operator override API
- **Validate via mass-balance + IMSR-replay tests as first-class
  acceptance criteria** (categorized variance per H2; Apr 24 `.jsonl`
  direct replay per H4)
- **Resolve DEF-014: HealthMonitor consumer + WebSocket fan-out + REST
  endpoint + acknowledgment flow + Dashboard banner + toast notifications
  + Observatory alerts panel + cross-page integration**, for ALL existing
  emitter sites (Databento + new `phantom_short*` from this sprint + IBKR
  emitter TODOs)

The sprint succeeds when (a) the operator daily-flatten mitigation
becomes safely removable based on mass-balance evidence from 3+ paper
sessions AND (b) the operator can see all critical alerts in the
Command Center without log-grep fallback.

## Phase A revisit results (informing this revision)

The OCA late-add behavior spike (`scripts/spike_ibkr_oca_late_add.py`)
ran on 2026-04-27 and produced **PATH_1_SAFE** unambiguously: IBKR's
matching engine rejects late-add OCA siblings with Error 201 "OCA group
is already filled" once any group member has filled. Sessions 1a + 1b
architecture is sound.

`reconstruct_from_broker()` has exactly one production call site
(`main.py:1081`, startup-only). No mid-session reconnect path exists
today; B3's catastrophic scenario is forward-looking, not present. Fix
simplifies to a contract docstring + Sprint 31.93 prerequisite.

Three B5 audit-row sites (Risk Manager, EOD Pass 2 short detection,
Health integrity check) are all side-blind broker-state reads needing
side-awareness. Same uniform pattern across the three sites.

Full Phase A findings: `PHASE-A-REVISIT-FINDINGS.md` in this folder.

## Session Breakdown (18 sessions, sequential)

The original 6-session plan grew to 10 (first revision), then to 12
(after Phase A's H3 split of 2b/2c), then to 17 (operator's Option 4
choice to fold DEF-014 alert observability all-in), and finally to 18
here after the third-pass adversarial review surfaced HIGH #1 — Session
5a was doing too much (6 distinct concerns + per-alert-type
auto-resolution policy) and at compaction score 12 was at risk of
mid-session emergency split. Splitting up front into 5a.1 + 5a.2 is
cheaper than splitting under compaction pressure. All sessions remain
sequential; the only variable is per-session reviewer focus (backend
safety reviewer for 0–4 + 5a.1 + 5a.2 + 5b; frontend reviewer for
5c–5e).

### Sessions 0–4 — DEF-204 mechanism closure (12 sessions; described in detail in `session-breakdown.md`)

- **Session 0** — `Broker.cancel_all_orders(symbol, *, await_propagation: bool = False)` API extension. ABC + 3 impls. AlpacaBroker stub via `DeprecationWarning` per L1.
- **Session 1a** — Bracket OCA grouping. `ManagedPosition.oca_group_id` field. SimulatedBroker no-op support. + Error 201/OCA-filled defensive handling on T1/T2 (per spike Trial 2/3 observation).
- **Session 1b** — Standalone-SELL OCA threading across 4 paths (`_trail_flatten`, `_escalation_update_stop`, `_resubmit_stop_with_retry`, `_flatten_position`). + Error 201 graceful handling (log INFO, mark redundant exit, do NOT trigger DEF-158 retry).
- **Session 1c** — Broker-only paths safety. `await_propagation=True` on the three SELL sites. `reconstruct_from_broker()` gets contract docstring (B3 simplification — no `ReconstructContext` enum needed today).
- **— Tier 3 architectural review #1 (after 1c) —** OCA-architecture-complete seal.
- **Session 2a** — Reconciliation contract refactor. `ReconciliationPosition` frozen dataclass. Line refs updated to current `:1505-1535` (was `:1412` in audit, drifted).
- **Session 2b.1** — Broker-orphan SHORT branch + `phantom_short` alert + `_broker_orphan_long_cycles` infrastructure. M2 lifecycle (cleanup on broker-zero / exponential backoff re-alert / reset on session start).
- **Session 2b.2** — Side-aware reads (THREE sites): margin-circuit reset + Risk Manager position cap + EOD Pass 2 alert emission + Health integrity check. Same side-aware-filter pattern across all three.
- **Session 2c.1** — Per-symbol gate state + handler + per-symbol granularity + M5 SQLite persistence (`phantom_short_gated_symbols` table in `data/operations.db`).
- **Session 2c.2** — Clear-threshold + auto-clear logic. Default `5` (was 3) per M4 cost-of-error asymmetry.
- **Session 2d** — Operator override API (`POST /api/v1/reconciliation/phantom-short-gate/clear`) + audit-log schema (M3) + always-fire-both-alerts (L3 — no suppression). **CLI tool dropped** since Sessions 5a–5e deliver proper UI.
- **Session 3** — DEF-158 retry side-check + severity fix. 3-branch pattern. `phantom_short_retry_blocked` severity critical.
- **Session 4** — Mass-balance categorized variance script (H2: `expected_partial_fill` / `eventual_consistency_lag` / `unaccounted_leak`) + IMSR replay using the available Apr 24 `.jsonl` (H4: synthetic-recreation language removed entirely). Live-enable gate criteria added to `pre-live-transition-checklist.md`.

### Sessions 5a.1–5e — Alert observability (DEF-014 full resolution; 6 sessions, frontend split out per reviewer focus)

- **Session 5a.1** — HealthMonitor consumer + REST endpoints + alert state model + AlertsConfig. **Backend.** `HealthMonitor` subscribes to `SystemAlertEvent`. REST endpoints: `GET /api/v1/alerts/active`, `GET /api/v1/alerts/history`, `POST /api/v1/alerts/{alert_id}/acknowledge`. Acknowledgment flow with audit-log entry per atomic-transition + idempotency contract (per third-pass MEDIUM #10). New `AlertsConfig` Pydantic model. Compaction score ~8.
- **Session 5a.2** — WebSocket fan-out + SQLite persistence + restart recovery + auto-resolution policy table. **Backend.** `WS /ws/v1/alerts` real-time fan-out. `alert_state` SQLite table for restart recovery. **Auto-resolution policy table** (per third-pass HIGH #1) — explicit per-alert-type cleared-condition: `phantom_short` (5 cycles zero-shares for symbol), `stranded_broker_long` (broker reports zero for symbol), `phantom_short_retry_blocked` (NEVER auto — requires operator ack), `cancel_propagation_timeout` (one-shot critical, requires operator ack), `ibkr_disconnect`/`ibkr_auth_failure` (successful subsequent operation), `databento_dead_feed` (3 healthy heartbeats). Retention policy + VACUUM strategy for `data/operations.db` (per third-pass MEDIUM #9). Compaction score ~9.
- **Session 5b** — Resolve IBKR emitter TODOs (`argus/execution/ibkr_broker.py:453,531`) + end-to-end integration tests. **Backend completion.** Alpaca emitter TODO (`argus/data/alpaca_data_service.py:593`) explicitly excluded — gets resolved by deletion in Sprint 31.94. End-to-end tests assert: emit → HealthMonitor consume → REST exposure → WebSocket push → acknowledgment → audit-log persistence. **Behavioral anti-regression test** (per third-pass MEDIUM #13) replaces line-number-based textual assertion: `inspect.getsource(alpaca_data_service)` must not contain `"SystemAlertEvent"`.
- **— Tier 3 architectural review #2 (after 5b) —** Alert-observability-backend seal. Validates the consumer architecture before frontend builds on it.
- **Session 5c** — Frontend `useAlerts` hook + Dashboard banner. **Frontend.** WebSocket subscription pattern follows `useObservatory` / `useArena`. Banner persists at top of Dashboard for any active critical alert. Includes acknowledgment button. **Phase D prerequisite (per third-pass HIGH #3):** `templates/review-prompt-frontend.md` authored in workflow metarepo with explicit checklist (state-machine completeness; reconnect/disconnect resilience; acknowledgment race handling; accessibility — ARIA, keyboard, focus trap; cross-page persistence; z-index/layout interactions; Vitest coverage thresholds) before this session begins.
- **Session 5d** — Toast notification system + acknowledgment UI flow. **Frontend.** New critical alerts pop up as toasts on any page when they arrive. Toast persists until acknowledged or auto-dismisses on condition-cleared. Acknowledgment flow writes audit-log entry.
- **Session 5e** — Observatory alerts panel + cross-page integration. **Frontend.** History view of all alerts in Observatory page. Banner from 5c becomes visible across all 10 pages (not just Dashboard) via shared layout component. Integration tests assert banner persistence across navigation.

## Key Decisions (revised, 2nd pass)

Decisions from the prior plans that survive unchanged:

- Naming reform: `sprint-31.91-reconciliation-drift` (etc.).
- Work on `main`, not feature branch.
- Monotonic-safety property at each session merge.
- @reviewer file-writing pattern: reviewer-writes-file.
- `ReconciliationPosition` frozen dataclass.
- Consume existing `Position.side`; do not add `Position.broker_side`.
- Reserve DEC-385 (side-aware reconciliation contract) and DEC-386
  (OCA-group threading).
- `bracket_oca_type` config accepts 0 or 1 only (operator footgun
  avoidance; ocaType=2 reduce-quantity semantics wrong for ARGUS bracket
  model).

New or revised decisions from the second pass / Phase A revisit:

- **`Broker.cancel_all_orders(symbol, *, await_propagation: bool = False)`**
  signature extension (B2). When `True`, polls broker open-orders for
  symbol until empty (2s timeout). Session 1c sites use `True`. On
  timeout, abort SELL + emit `cancel_propagation_timeout` alert.
- **No `ReconstructContext` enum needed today** (B3). `reconstruct_from_broker()`
  is currently startup-only; gets a contract docstring requiring future
  callers to add context-awareness. Sprint 31.93 roadmap entry gains this
  as a prerequisite.
- **Error 201 / "OCA group is already filled" is the success signature.**
  Sessions 1a + 1b add defensive handling that distinguishes this
  specific reason from generic Error 201 (margin, etc.) and treats it
  as SAFE failure (log INFO, mark redundant).
- **Three-site B5 pattern: Risk Manager + EOD Pass 2 + Health integrity
  check.** All side-blind broker-state reads; all need side-aware filter.
  Same pattern. All fold into Session 2b.2.
- **Sessions 2b/2c split** (H3 pre-empt). 2b.1 / 2b.2 / 2c.1 / 2c.2.
- **Default `broker_orphan_consecutive_clear_threshold: 5`** (was 3).
  Cost-of-error asymmetry: phantom-short re-engagement is strictly
  worse than DEC-370's miss-counter false positive (per M4).
- **Per-symbol gate persists to SQLite** via `data/operations.db`
  `phantom_short_gated_symbols` table. Rehydrated on startup BEFORE
  OrderManager processes events. Closes the 60s window of unsafe
  entries on restart (per M5).
- **Operator override audit-log schema specified** (M3): `phantom_short_override_audit`
  table in `data/operations.db` with `(timestamp_utc, timestamp_et,
  symbol, prior_engagement_source, prior_engagement_alert_id, reason_text,
  override_payload_json)`.
- **DEF-014 fully resolved in this sprint** (Sessions 5a–5e). M6 dispositioned
  as **FULL ACCEPT (all-in)**, not deferred. CLI tool dropped from Session
  2d scope (the proper UI is in 5c–5e). Live-enable gate simplifies — no
  deferred prerequisites for Command Center surface. Alpaca emitter TODO
  excluded from scope (resolved by deletion in 31.94).
- **Live-enable gate decomposes to four criteria** (per third-pass HIGH
  #4; was three with one ambiguous):
  1. ≥3 paper sessions with zero `unaccounted_leak` mass-balance rows
  2. AND zero `phantom_short` alerts across those sessions
  3. **(NEW 3a — pre-live paper stress test):** ≥1 paper-trading
     session under live-config simulation (paper-trading data-capture
     overrides removed; risk limits restored; overflow capacity
     restored; ≥10 entries placed); zero `phantom_short` alerts; zero
     `unaccounted_leak` mass-balance rows.
  4. **(NEW 3b — live rollback policy, was the original criterion #3
     reframed):** First live trading session caps position size at
     **$50–$500 notional** on a single operator-selected symbol. Any
     `phantom_short*` or `phantom_short_retry_blocked` alert during
     the window triggers immediate suspension via operator-manual
     halt (formal `POST /api/v1/system/suspend` deferred — see new
     DEF-210 below). After session-end clean, expand to standard
     sizing on day 2.
  5. ~~~~Disconnect-reconnect leg~~~~ — moved to Sprint 31.93's gate (B3)
- **Mass-balance categorized variance** (H2). `expected_partial_fill`
  (no flag), `eventual_consistency_lag` (no flag, ≤1 reconciliation cycle
  window), `unaccounted_leak` (flag, exit non-zero). 5-share tolerance
  framing dropped.
- **Reverse-rollback escape hatch becomes restart-required** (H1).
  `bracket_oca_type: 0` flip requires operator restart so all in-flight
  positions reconstruct under new config. Documented in runbook.
- **Apr 24 paper-session log confirmed at `logs/argus_20260424.jsonl`**
  (operator-confirmed). H4's synthetic-recreation language removed
  entirely; the IMSR replay test uses the real log directly.
- **Two Tier 3 architectural reviews** (was 1): after 1c (OCA-architecture
  seal) and after 5b (alert-observability backend seal). Frontend Sessions
  5c–5e do not get a third Tier 3; they have a different reviewer focus
  and the architectural seam is at 5b.

## Scope Boundaries (revised, 2nd pass)

### IN scope (18 sessions)

All deliverables from prior plans, plus:

- `Broker.cancel_all_orders(symbol, await_propagation)` API extension
- `_flatten_position` OCA threading
- `_flatten_unknown_position`, `_drain_startup_flatten_queue`,
  `reconstruct_from_broker()`, EOD Pass 2 broker-only safety
- Margin circuit side-aware reset
- Risk Manager position cap side-aware filter (NEW B5 site #1)
- EOD Pass 2 short detection emits `phantom_short` alert (NEW B5 site #2)
- Health integrity check side-aware (NEW B5 site #3)
- Per-symbol gate clear-threshold = 5 + SQLite persistence
- Operator override API + audit-log schema + always-both-alerts
- Mass-balance categorized variance script + IMSR replay using Apr 24
  `.jsonl` direct
- Performance Considerations documentation + restart-required rollback
- Error 201 / OCA-filled defensive + graceful handling (Sessions 1a + 1b)
- Contract docstring on `reconstruct_from_broker()` (B3)
- **HealthMonitor consumer + WebSocket fan-out + REST endpoint +
  acknowledgment flow** (Session 5a)
- **IBKR emitter TODOs resolved + end-to-end integration tests** (Session 5b)
- **Frontend `useAlerts` hook + Dashboard banner** (Session 5c)
- **Toast notifications + acknowledgment UI** (Session 5d)
- **Observatory alerts panel + cross-page integration** (Session 5e)

### OUT of scope (do NOT modify) — refined

- DEF-199 A1 fix (`order_manager.py:1670-1750`)
- IMPROMPTU-04 startup invariant (`main.py` startup region except scoped
  Session 1c docstring + Session 2a reconciliation call site)
- `Position.shares` Pydantic constraint
- `argus/execution/alpaca_broker.py` business logic (Session 0 adds
  `cancel_all_orders(symbol)` ABC compliance via `DeprecationWarning`;
  nothing else)
- **`argus/data/alpaca_data_service.py:593` Alpaca emitter TODO** — gets
  resolved by deletion in Sprint 31.94, not by wiring in 31.91
- DEF-194/195/196 reconnect-recovery (Sprint 31.93)
- DEF-175/182/201/202 component ownership (Sprint 31.92)
- Re-enabling live trading (downstream gate)
- `_resubmit_stop_with_retry` retry-cap logic (DEC-372 — only OCA threading is added)

### Newly deferred (filed as DEFs at sprint close)

- **DEF-208** — SimulatedBroker should simulate OCA-group cancellation
  semantics matching ocaType=1 to align backtest fill behavior with
  live. Until then, post-31.91 backtest T2-hit rates are upper bounds.
  *Note: spike script remains in repo as live-IBKR regression check;
  partially mitigates DEF-208's risk for OCA-mechanism specifically.*
- **DEF-209** — `analytics/debrief_export.py` and other historical-record
  writers must preserve `Position.side` to support side-aware Learning
  Loop V2.
- **DEF-210 (NEW per third-pass HIGH #4)** — `POST /api/v1/system/suspend`
  endpoint to allow live-rollback policy (3b) automation. Until then,
  operator manually halts ARGUS via standard shutdown sequence on any
  `phantom_short*` alert during the first-day-live window.
- **DEF-211 (NEW per third-pass LOW #14)** — Side-aware breakdown in
  post-flatten verification log line at `order_manager.py:1729`. The
  current "Remaining symbols: [...]" log conflates EOD-flatten failures
  with phantom-short residue. Not safety-critical (informational only,
  no order placed); file for future operator-experience work.

### Phase D Open Items (third-pass MEDIUM/LOW captured for in-flight inclusion)

See `PHASE-D-OPEN-ITEMS.md` for the full list of MEDIUM/LOW findings
from the third-pass review that don't change Phase C artifact shape
but MUST be incorporated into Phase D implementation prompts. Top
items: IMPROMPTU-04 row #4 grep verification (Session 4 prompt); EOD
Pass 2 cancel-timeout failure-mode documentation (Session 1c prompt);
Health + broker-orphan double-fire dedup decision (operator); mass-
balance category precedence rules (Session 4 prompt); Session 2a
mock-update grep (Session 2a pre-flight).

## Regression Invariants (revised, 2nd pass)

Original 9 + first-revision 10–11 unchanged. New invariants from this
revision:

12. **Bracket placement performance** does not regress beyond the
    documented 50–200ms fill-latency cost on cancelling siblings.
    Measured at debrief.
13. **Mass-balance** assertion at session debrief (categorized variance,
    not single threshold): zero `unaccounted_leak` rows per symbol per
    session. `expected_partial_fill` and `eventual_consistency_lag`
    permitted but logged.
14. **Error 201 / OCA-filled handling** does not produce false-negative
    treatment of generic Error 201 (margin rejections, price
    protection, etc.). Distinguishing test asserts both code paths fire
    correctly.
15. **Per-symbol gate persistence** survives ARGUS restart. After
    rehydration, gated symbols continue to block entries until either
    auto-clear (5 cycles) or operator override.
16. **Alert acknowledgment audit trail** persists across restarts. After
    operator acknowledges an alert and ARGUS restarts, the audit-log
    entry is still queryable.
17. **Frontend banner cross-page persistence** — banner remains visible
    when navigating between Command Center pages while a critical alert
    is active. Banner clears within 1s of acknowledgment OR
    condition-resolution.
18. **WebSocket alert fan-out reconnect resilience** — if the WebSocket
    connection drops, the frontend reconnects and fetches current state
    via `GET /api/v1/alerts/active` to recover any alerts emitted
    during the disconnect window.

The monotonic-safety state matrix grows from 11 rows (post 1st revision)
to 18 rows (one per session). Each row strictly safer than the row
above. See `regression-checklist.md` for the full matrix.

## File Scope (revised, 2nd pass)

### Modify (backend)

- `argus/execution/broker.py` (ABC `cancel_all_orders(symbol, await_propagation)` extension — Session 0)
- `argus/execution/ibkr_broker.py` (bracket placement Session 1a; `cancel_all_orders` impl Session 0; emitter TODOs Session 5b)
- `argus/execution/alpaca_broker.py` (Session 0 `DeprecationWarning` only; no other changes)
- `argus/execution/simulated_broker.py` (Session 0 impl; mock OCA support Session 1a)
- `argus/execution/order_manager.py` (heavy lifter — touched by 1a, 1b, 1c, 2a, 2b.1, 2b.2, 2c.1, 2c.2, 3)
- `argus/core/risk_manager.py` (B5 site #1 — Session 2b.2)
- `argus/core/health.py` (B5 site #3 — Session 2b.2; HealthMonitor consumer expansion — Session 5a)
- `argus/main.py` (reconcile call site Session 2a; startup gate rehydration Session 2c.1; HealthMonitor consumer init Session 5a)
- `argus/api/` reconciliation router (Session 2d); alerts router NEW (Session 5a.1)
- `argus/ws/` alerts WebSocket NEW (Session 5a.2)
- Pydantic config models (6 new fields total: `bracket_oca_type`, `broker_orphan_alert_enabled`, `broker_orphan_entry_gate_enabled`, `broker_orphan_consecutive_clear_threshold`, `phantom_short_aggregate_alert_threshold` (LOW #15), `alerts.acknowledgment_required_severities`, `alerts.auto_resolve_on_condition_cleared`, `alerts.audit_log_retention_days`, `alerts.archived_alert_retention_days` — last two per MEDIUM #9)
- `data/operations.db` schema additions (4 new tables: `phantom_short_gated_symbols`, `phantom_short_override_audit`, `alert_acknowledgment_audit`, `alert_state` — last per MEDIUM #9 restart-recovery)
- `data/operations.db` schema-version table + migration registry (NEW per MEDIUM #9; first migration framework in ARGUS)
- VACUUM scheduling for `data/operations.db` (mirror Sprint 31.8 S2 evaluation.db pattern; per MEDIUM #9)
- Test files — extensively, see Session Breakdown for per-session counts

### Modify (frontend)

- `frontend/src/hooks/useAlerts.ts` NEW (Session 5c)
- `frontend/src/components/AlertBanner.tsx` NEW (Session 5c)
- `frontend/src/components/AlertToast.tsx` NEW (Session 5d)
- `frontend/src/components/AlertAcknowledgmentModal.tsx` NEW (Session 5d)
- `frontend/src/pages/Observatory.tsx` (alerts panel addition — Session 5e)
- `frontend/src/components/Layout.tsx` (banner cross-page mount — Session 5e)
- Vitest test files — extensively for 5c–5e

### Modify (docs, in-sprint deliverables)

- `docs/live-operations.md` (Session 2d phantom-short runbook; Session 5a.1 alert acknowledgment runbook)
- `docs/pre-live-transition-checklist.md` (Session 4 live-enable gate criteria)
- `docs/protocols/market-session-debrief.md` (Session 4 Phase 7 slippage watch + alert summary)

### Do NOT modify — unchanged from prior list

## Config Changes (revised, 2nd pass)

| YAML path | Pydantic model | Field name | Default | Accepts | Session |
|---|---|---|---|---|---|
| `ibkr.bracket_oca_type` | `IBKRConfig` | `bracket_oca_type` | `1` | 0 or 1 | 1a |
| `reconciliation.broker_orphan_alert_enabled` | `ReconciliationConfig` | `broker_orphan_alert_enabled` | `true` | bool | 2b.1 |
| `reconciliation.broker_orphan_entry_gate_enabled` | `ReconciliationConfig` | `broker_orphan_entry_gate_enabled` | `true` | bool | 2c.1 |
| `reconciliation.broker_orphan_consecutive_clear_threshold` | `ReconciliationConfig` | `broker_orphan_consecutive_clear_threshold` | `5` | int ≥1 | 2c.2 |
| `reconciliation.phantom_short_aggregate_alert_threshold` | `ReconciliationConfig` | `phantom_short_aggregate_alert_threshold` | `10` | int ≥1 | 2d (LOW #15) |
| `alerts.acknowledgment_required_severities` | `AlertsConfig` (NEW) | `acknowledgment_required_severities` | `["critical"]` | list[str] | 5a.1 |
| `alerts.auto_resolve_on_condition_cleared` | `AlertsConfig` | `auto_resolve_on_condition_cleared` | `true` | bool | 5a.2 |
| `alerts.audit_log_retention_days` | `AlertsConfig` | `audit_log_retention_days` | `null` (forever) | int or null | 5a.2 (MEDIUM #9) |
| `alerts.archived_alert_retention_days` | `AlertsConfig` | `archived_alert_retention_days` | `90` | int ≥1 | 5a.2 (MEDIUM #9) |

## Test Strategy (revised, 2nd pass)

| Session | New pytest tests | New Vitest tests | Mock updates | Total delta |
|---|---:|---:|---:|---:|
| 0 (`cancel_all_orders` API) | ~6 | 0 | ~3 | +6 to +9 |
| 1a (bracket OCA + Error 201) | ~8 | 0 | ~1 | +8 to +9 |
| 1b (standalone-SELL + Error 201) | ~8 | 0 | 0 | +8 |
| 1c (broker-only paths) | ~6 | 0 | ~1 | +6 to +7 |
| 2a (recon contract) | ~5 | 0 | ~3 | +5 to +8 |
| 2b.1 (broker-orphan + cycle infra) | ~6 | 0 | 0 | +6 |
| 2b.2 (4 count-filter sites + 1 alert-alignment) | ~9 | 0 | 0 | +9 |
| 2c.1 (gate state + persistence) | ~6 | 0 | 0 | +6 |
| 2c.2 (clear-threshold) | ~4 | 0 | 0 | +4 |
| 2d (override API + audit + threshold config) | ~6 | 0 | 0 | +6 |
| 3 (DEF-158 retry side-check) | ~5 | 0 | ~2 | +5 to +7 |
| 4 (mass-balance + IMSR replay) | ~5 | 0 | 0 | +5 |
| **5a.1 (HealthMonitor + REST + ack)** | ~7 | 0 | ~1 | +7 to +8 |
| **5a.2 (WebSocket + persistence + auto-resolution + retention)** | ~7 | 0 | ~1 | +7 to +8 |
| 5b (IBKR emitters + E2E + behavioral Alpaca check) | ~8 | 0 | ~2 | +8 to +10 |
| 5c (`useAlerts` hook + banner) | 0 | ~10 | 0 | +10 Vitest |
| 5d (toast + ack UI) | 0 | ~8 | 0 | +8 Vitest |
| 5e (Observatory panel + cross-page) | 0 | ~8 | 0 | +8 Vitest |
| **Total** | | | | **+104 pytest, +34 Vitest** |

Final pytest baseline target: **~5,180 to ~5,200** (from 5,080).
Final Vitest baseline target: **~900** (from 866).

## Compaction Risk Assessment (preliminary, revised, 2nd pass)

| Session | Created | Modified | Pre-flight reads | Tests | Integration | Score | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 0 | 4 | 5 | 6–9 | +1 | ~7 | proceed |
| 1a | 0 | 3 | 5 | 8–9 | +1 | ~9.5 | proceed |
| 1b | 0 | 1 (4 fns) | 4 | 8 | +1 | ~9 | proceed |
| 1c | 0 | 1 (3 fns) | 5 | 6–7 | +2 | ~9 | proceed |
| 2a | 1 | 2 | 6 | 5–8 | +2 | ~10.5 | proceed |
| 2b.1 | 0 | 2 | 5 | 6 | +2 | ~8 | proceed |
| 2b.2 | 0 | 3 | 6 | 9 | +1 | ~10 | proceed |
| 2c.1 | 1 (db tbl) | 2 | 5 | 6 | +2 | ~9 | proceed |
| 2c.2 | 0 | 2 | 4 | 4 | +1 | ~6 | proceed |
| 2d | 1 (route) + 1 (db tbl) | 3 | 5 | 6 | +2 | ~9 | proceed |
| 3 | 0 | 1 | 4 | 5 | 0 | ~6 | proceed |
| 4 | 2 (script + test) | 2 (docs) | 4 | 5 | +1 | ~7 | proceed |
| **5a.1** | 1 (route) + 1 (db tbl) | 2 | 5 | 7–8 | +1 | **~8** | proceed |
| **5a.2** | 1 (ws) + 1 (db tbl) | 2 | 5 | 7–8 | +2 | **~9** | proceed |
| 5b | 0 | 2 | 5 | 8–10 | +3 | ~9 | proceed |
| 5c | 2 (hook + banner) | 1 | 5 | 10 (Vitest) | +1 | ~9 | proceed |
| 5d | 2 (toast + modal) | 1 | 4 | 8 (Vitest) | +1 | ~8 | proceed |
| 5e | 0 | 2 (Observatory + Layout) | 5 | 8 (Vitest) | +1 | ~8 | proceed |

Highest score: 2a at ~10.5 (well under 14 threshold). Splitting 5a from
~12 to ~8 + ~9 removes the prior highest-score session and absorbs the
auto-resolution policy work + retention/migration policy work without
mid-session compaction pressure. No further splits anticipated; final
scoring with full Creates/Modifies enumeration in Session Breakdown.

## Performance Considerations (REVISED — H1 disposition)

`ocaType=1` ("Cancel with block") atomically blocks fills on OCA siblings
when one member fills, until cancellation propagation completes across
sibling order books at IBKR's matching engine. Production IBKR latency
for this propagation is typically 50–200ms (paper-trading documented as
looser).

**Phase A spike confirmed** (`scripts/spike_ibkr_oca_late_add.py`,
2026-04-27): IBKR's enforcement is even stricter — once any OCA group
member has filled, *all* subsequent same-group submissions are rejected
with Error 201 "OCA group is already filled," including same-batch
siblings if they lose the microsecond race against fill propagation.
The OCA group transitions into a terminal "filled" state. This means
late-add SELLs cannot accidentally fill against zero broker position.

This cost falls on the **cancelling siblings**, not the order that fired
first. The order that triggered cancellation fills at its normal price.

**Architectural justification for ocaType=1 over ocaType=2:** ARGUS's
bracket model places T1 and T2 at distinct full-quantity price targets.
ocaType=2's "Reduce with block" reduce-quantity semantics would mean a
T1 partial fill silently reduces T2's remaining quantity — wrong for
ARGUS, where T2 should retain its quantity. Native IBKR `parentId`
linkage handles partial-fill T2-stays-alive orthogonally; ocaType=1 adds
atomic cancellation when one OCA member fills FULLY (not partially).

**Trade-off acknowledged:** for tight-stop momentum strategies (ORB
Scalp, Micro Pullback, GapAndGo), the 50–200ms cancellation propagation
can mean fills at slightly worse prices on cancelling siblings during
fast moves. The correctness benefit (atomic cancellation prevents the
IMSR-style multi-leg fill race that produced 14,249 phantom shorts on
Apr 24) outweighs this cost.

**Reverse-rollback escape hatch (RESTART-REQUIRED, per H1):**
`ibkr.bracket_oca_type: 0` disables OCA on bracket children, restoring
pre-sprint behavior on bracket-side. **Mid-session config flip is NOT
supported** — produces an inconsistent cohort of in-flight positions.
Operator must restart so all positions reconstruct under the new config.
Documented in `docs/live-operations.md` runbook section.

**Post-merge regression check** added to Session 4 deliverables: compare
mean slippage on bracket-stop fills pre vs post Sprint 31.91; flag if
mean degrades by >$0.02 on $7–15 share universe. Triggers evaluation of
restart-required rollback if degradation observed.

## Mass-Balance + IMSR Replay (REVISED — H2/H4 dispositions)

Per second-pass Findings #5/#H2/#H4, mass-balance validation graduates
from a single-tolerance assertion to a categorized variance report
(H2). Three categories:

- **`expected_partial_fill`** — ARGUS placed N shares, M filled (M < N),
  order is still working. No flag.
- **`eventual_consistency_lag`** — ARGUS-side accounting lags broker-side
  by ≤ 1 reconciliation cycle (60s). No flag.
- **`unaccounted_leak`** — Shares in broker SELL stream not attributable
  to either of the above. **Flag**, regardless of size. Mass-balance
  script exits non-zero on any `unaccounted_leak` row.

The 5-share tolerance framing is dropped entirely. Live-enable gate:
zero `unaccounted_leak` rows across 3+ paper sessions.

**IMSR replay test (H4):** Apr 24 paper-session log confirmed available
at `logs/argus_20260424.jsonl` (operator-confirmed). Replay through
BacktestEngine harness with post-fix code; assert IMSR EOD position is
0 (not −200). Synthetic-recreation language removed entirely; the test
uses the real log directly.

**Live-IBKR mechanism check (B1/B4):** The OCA late-add spike script
(`scripts/spike_ibkr_oca_late_add.py`) is committed to the repo as a
re-runnable regression check. Operator runs against IBKR paper at any
time to verify OCA semantics haven't drifted (e.g., after IBKR API
updates, after major IBKR Gateway version changes). Three trial variants
in ~60 seconds.

## Runner Compatibility

- **Mode:** Human-in-the-loop. No runner config.
- **Parallelizable sessions:** None. Backend Sessions 0–4 + 5a–5b touch
  shared backend code. Frontend Sessions 5c–5e touch shared frontend
  layout / hook patterns. Full sequential execution required.
- **Token budget estimate:** 18 sessions × ~13K (impl prompt + closeout
  + Tier 2 review) + 2 Tier 3 architectural reviews × ~10K + buffer
  ~15K = **~260K tokens total**.
- **Sprint duration estimate:** 7–8 weeks. Operator daily-flatten
  mitigation continues throughout.
- **Reviewer split:** Backend safety reviewer for Sessions 0–4 + 5a.1
  + 5a.2 + 5b. Frontend reviewer (different @reviewer subagent or
  human reviewer with frontend focus) for Sessions 5c–5e. Each
  implementation prompt flags the expected reviewer focus. **Phase D
  prerequisite (HIGH #3): `templates/review-prompt-frontend.md`
  authored in workflow metarepo before Session 5c begins.**

## Dependencies

- [ ] Sprint folder rename completed (already done in prior pass)
- [ ] Cross-reference rename patches applied per `doc-update-checklist.md`
      Phase A
- [ ] **Phase C-1 third-pass adversarial review** — done after revised
      artifacts ship and before Phase D begins. Operator confirmed.
- [ ] DEF-204 still OPEN in CLAUDE.md
- [ ] Operator daily flatten mitigation in effect throughout sprint window
- [ ] `ib_async` `ocaGroup` / `ocaType` field support verified
- [ ] **Apr 24 paper-session log confirmed available at
      `logs/argus_20260424.jsonl`** (operator-confirmed 2026-04-27)
- [ ] **OCA late-add spike result `PATH_1_SAFE` confirmed** (2026-04-27)
- [ ] `main` HEAD on a known-green CI commit at session start
- [ ] Adversarial Tier 2 reviewer engaged for all 18 sessions
- [ ] **Tier 3 architectural reviewer engaged after Session 1c lands**
      (review #1)
- [ ] **Tier 3 architectural reviewer engaged after Session 5b lands**
      (review #2)
- [ ] **Frontend reviewer arrangements confirmed for Sessions 5c–5e**
      (different focus from backend safety reviewer)
- [ ] **`templates/review-prompt-frontend.md` authored in workflow
      metarepo** before Session 5c begins (Phase D prerequisite per
      third-pass HIGH #3). Checklist: state-machine completeness;
      reconnect/disconnect resilience; acknowledgment race handling;
      accessibility (ARIA, keyboard, focus trap); cross-page
      persistence; z-index/layout interactions; Vitest coverage
      thresholds.
- [ ] **Spike script trigger registry documented in
      `docs/live-operations.md`** (Phase D prerequisite per third-pass
      HIGH #5). Re-run `scripts/spike_ibkr_oca_late_add.py` before:
      live-trading transition (live-enable gate item); `ib_async`
      version upgrade; IBKR API version change; monthly during
      paper-trading windows. Spike result file dated within last
      30 days when in paper-trading mode.

## Escalation Criteria (high-level — full detail in `escalation-criteria.md`)

- Mandatory Tier 3 #1 after Session 1c (OCA architecture seal). **Scope
  per third-pass LOW #17: combined diff of Sessions 0 + 1a + 1b + 1c**
  (the API contract introduced in Session 0 is part of the OCA
  architecture; reviewing without it would be incomplete).
- Mandatory Tier 3 #2 after Session 5b (alert observability backend
  seal). Scope: combined diff of Sessions 5a.1 + 5a.2 + 5b.
- Any Tier 2 CONCERNS or ESCALATE → operator review.
- Paper-session debrief shows ANY phantom-short accumulation post-merge
  → revert + ad-hoc Tier 3.
- DEC-117 atomic-bracket invariant change → halt, escalate.
- OCA-group lifecycle race surfaced during implementation → halt, escalate.
- Per-symbol entry gate deadlock → halt, escalate.
- Mass-balance regression in Session 4 validation → halt, escalate.
- IMPROMPTU-04 grep-audit row produces a finding → halt, escalate.
- Bracket placement performance regression beyond documented 50–200ms →
  halt, evaluate restart-required `bracket_oca_type: 0` rollback.
- **WebSocket fan-out reconnect loses alert state without REST recovery
  → halt, escalate** (alert observability invariant).
- **Frontend banner fails to persist across page navigation → halt,
  escalate** (alert observability invariant 17).

## Doc Updates Needed (post-sprint, expanded)

Original 9 + first-revision additions, plus:

- `docs/live-operations.md` — phantom-short runbook section (Session 2d,
  in-sprint) + alert acknowledgment runbook (Session 5a, in-sprint) +
  restart-required rollback note (H1, in-sprint via Session 1a).
- `docs/pre-live-transition-checklist.md` — live-enable gate criteria
  (Session 4, in-sprint).
- `docs/architecture.md` §3.3 — `cancel_all_orders` signature change
  (Session 0).
- `docs/architecture.md` §13 (Observatory) — alerts panel addition
  (Session 5e).
- `docs/architecture.md` §14 (alert observability) NEW SECTION —
  HealthMonitor consumer + WebSocket fan-out + REST endpoint design
  (Session 5a).
- New DEFs filed: DEF-208, DEF-209.
- **DEF-014 marked CLOSED** in CLAUDE.md DEF table (sprint-close doc-sync).

## Artifacts to Generate (revised, 2nd pass)

### Phase B (revised, 2nd pass) — this document

### Phase C (revised, 2nd pass, regenerating in order)

1. Sprint Spec (revised — all D1–D8 expand to D1–D14; Sessions 5a–5e add
   D9–D14; live-enable gate simplifies; mass-balance reframes)
2. Specification by Contradiction (revised — alert observability scope
   in; DEF-208/209 still in deferred; Alpaca emitter explicitly out)
3. Session Breakdown (revised — 18 sessions with full
   Creates/Modifies/Integrates; reviewer split annotated; 5a split
   into 5a.1 + 5a.2 per third-pass HIGH #1)
4. Sprint-Level Escalation Criteria (revised — Tier 3 #2 trigger; new
   alert observability invariants; A11/A12/A13 added per HIGH #3/#4/#5)
5. Sprint-Level Regression Checklist (revised — invariants 12–22 added,
   19-row monotonic-safety state matrix, frontend Vitest checks)
6. Doc Update Checklist (revised — DEF-014 closure section, in-sprint
   doc deliverables expanded, Alpaca emitter explicitly excluded)
7. Adversarial Review Input Package — append SECOND Revision Rationale
   section summarizing the 5 BLOCKING + 4 HIGH + 6 MEDIUM + 3 LOW
   findings and dispositions (cumulative with first-pass section)

### Phase C-1 (third pass) — operator-run separate Claude.ai conversation

- Run adversarial review on revised artifacts 1–2 + revised input package
- If clears with minor observations only: proceed to Phase D
- If revisions needed: another iteration; if more BLOCKING surfaces:
  diagnostic of deeper issue (escalation)

### Phase D (after C-1 third pass clears)

- Review Context File
- Implementation Prompt × 17 (one per session) — backend reviewer
  flagged for 0–4 + 5a–5b; frontend reviewer flagged for 5c–5e
- Tier 2 Review Prompt × 17
- Work Journal Handoff Prompt

---

*End Sprint 31.91 design summary (revised, 3rd pass — 18-session shape).*
