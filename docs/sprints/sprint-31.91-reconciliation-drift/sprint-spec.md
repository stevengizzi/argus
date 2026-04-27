# Sprint 31.91: Reconciliation Drift — DEF-204 Fix + DEF-014 Resolution (REVISED 3rd pass)

> **Phase C artifact 1/7 (revised 3rd pass).** Source of truth for what
> this sprint delivers. Companion: `spec-by-contradiction.md`,
> `session-breakdown.md`, `escalation-criteria.md`, `regression-checklist.md`,
> `doc-update-checklist.md`, `adversarial-review-input-package.md`,
> `design-summary.md`, `PHASE-A-REVISIT-FINDINGS.md`,
> `PHASE-D-OPEN-ITEMS.md`.

## Goal

Two related goals delivered together:

1. **Eliminate DEF-204's phantom-short cascade across all known surfaces**
   (Sessions 0–4) — bracket OCA + standalone-SELL OCA + broker-only
   safety + side-aware reconciliation contract + side-aware position cap
   / EOD detection / Health integrity check + DEF-158 retry side-check +
   mass-balance + IMSR replay validation.
2. **Resolve DEF-014 alert observability fully** (Sessions 5a.1–5e) —
   HealthMonitor consumer + REST endpoints + acknowledgment flow
   (5a.1); WebSocket fan-out + persistence + auto-resolution policy
   table + retention/migration (5a.2); IBKR emitter resolution + E2E
   (5b); Dashboard banner + toast notifications + Observatory alerts
   panel + cross-page integration (5c–5e). Wires both the pre-existing
   Databento emitter and the new `phantom_short*` emitters from this
   sprint.

The sprint succeeds when:

- Mass-balance shows zero `unaccounted_leak` rows across 3+ paper
  sessions
- Zero `phantom_short` alerts emitted across those sessions
- Operator can see all critical alerts in real-time in the Command
  Center (banner, toasts, Observatory panel) without log-grep fallback
- First-day-live monitored validation completes (smallest position size,
  single symbol)

After all four conditions: operator daily-flatten mitigation becomes
safely removable; live-trading consideration unblocked.

## Scope

### Deliverables (14 distinct deliverables across 18 sessions)

#### D1 — `Broker.cancel_all_orders(symbol, await_propagation)` API extension (Session 0)

Extend the `Broker` ABC's `cancel_all_orders()` signature to:
```python
async def cancel_all_orders(
    self, symbol: str | None = None, *, await_propagation: bool = False
) -> int
```

- `symbol=None` preserves DEC-364 contract (cancel everything).
- A symbol filters cancellation to that symbol's working orders only.
- `await_propagation=True` polls broker open-orders for the filtered
  scope until empty (default 2s timeout). On timeout, raises
  `CancelPropagationTimeout` exception so callers can abort the
  follow-up SELL placement.

Implementations: `IBKRBroker` (uses `ib_async`'s open-orders filter),
`AlpacaBroker` (DeprecationWarning per L1 — queued for retirement in
Sprint 31.94), `SimulatedBroker` (in-memory order filter).

#### D2 — Bracket OCA grouping + Error 201 defensive handling (Session 1a)

Bracket children (stop, T1, T2) submitted via
`IBKRBroker.place_bracket_order` carry `ocaGroup` (per-bracket
ULID-derived; specifically `f"oca_{parent_ulid}"` per M1 disposition)
and `ocaType == 1`. `oca_group_id` persists on `ManagedPosition` at
bracket-confirmation time. SimulatedBroker accepts and stores the new
Order fields.

**Defensive Error 201 handling on T1/T2 submission:** if T1 or T2
placement fails with IBKR Error 201 reason "OCA group is already filled"
(rare but possible if market moves fast enough for the stop to fill in
the bracket-placement micro-window), this is logged INFO not ERROR and
treated as a SAFE outcome — DEC-117 atomic-bracket rollback already
handles cancellation of any partially-placed children. Distinguished
from generic Error 201 (margin, price-protection, etc.) by parsing the
reason string.

#### D3 — Standalone-SELL OCA threading + Error 201 graceful handling (Session 1b)

Every SELL order placed by `_trail_flatten`, `_escalation_update_stop`,
`_resubmit_stop_with_retry`, AND `_flatten_position` for a
`ManagedPosition` with non-`None` `oca_group_id` carries that same
`ocaGroup` value. `_flatten_position` is the central path used by EOD
Pass 1, `close_position()` API, `emergency_flatten()`, and time-stop.

**Graceful Error 201/OCA-filled handling:** if any of these SELL
placements fails with Error 201 "OCA group is already filled," this
means the position is already exiting via another OCA member (e.g., the
bracket stop already triggered). Log INFO, mark as "redundant exit" in
ManagedPosition state, do NOT trigger DEF-158 retry path (Session 3's
side-check would catch the resulting zero-broker-position anyway, but
short-circuit is cleaner).

A grep-test regression guard asserts no `_broker.place_order(Order(...,
side=SELL))` call inside `argus/execution/order_manager.py` happens for
a symbol with a `ManagedPosition` carrying `oca_group_id` without
threading that group OR being in the permitted-exempt list (broker-only
paths Session 1c handles separately).

#### D4 — Broker-only SELL paths safety + reconstruct docstring (Session 1c)

For SELL paths where no `ManagedPosition` exists, invoke
`broker.cancel_all_orders(symbol=..., await_propagation=True)` BEFORE
placing the SELL to clear stale OCA-group siblings:

- `_flatten_unknown_position` — used by EOD Pass 2 + zombie cleanup
- `_drain_startup_flatten_queue` — startup zombie flatten

Plus extend `reconstruct_from_broker()` to invoke
`cancel_all_orders(symbol=..., await_propagation=True)` for each
reconstructed symbol BEFORE wiring into `_managed_positions`.

**Contract docstring on `reconstruct_from_broker()`:**

```
This function is currently STARTUP-ONLY and is called exactly once at
ARGUS boot via `argus/main.py:1081` (gated by `_startup_flatten_disabled`).
The unconditional `cancel_all_orders(symbol)` invocation is correct ONLY
in this startup context — it clears stale yesterday's OCA siblings before
today's session begins.

Future callers MUST add a context parameter (e.g., `ReconstructContext`)
distinguishing STARTUP_FRESH from RECONNECT_MID_SESSION. The
RECONNECT_MID_SESSION path MUST NOT invoke `cancel_all_orders` —
yesterday's working bracket children are LIVE this-session orders that
must be preserved.

Sprint 31.93 (DEF-194/195/196 reconnect-recovery) is the natural sprint
to add this differentiation. Until then, ARGUS does not support
mid-session reconnect; operator daily-flatten remains the safety net.
```

**Acceptance:** "After `cancel_all_orders(symbol=X, await_propagation=True)`
returns successfully, no working orders exist at IBKR for X. After
timeout, the follow-up SELL is not placed and a
`cancel_propagation_timeout` alert is emitted. After
`reconstruct_from_broker()` returns at startup, no working orders exist
at IBKR for any reconstructed symbol that did not exist at the start of
the call."

#### D5 — Side-aware reconciliation contract (Sessions 2a + 2b.1 + 2b.2 + 2c.1 + 2c.2 + 2d)

Contract refactor (2a):
- `OrderManager.reconcile_positions()` accepts
  `dict[str, ReconciliationPosition]` (frozen dataclass: `symbol`,
  `side`, `shares`) instead of `dict[str, float]`.
- Call site in `argus/main.py:1505-1535` updated.

Detection + alerts (2b.1):
- Orphan loop extended with broker-orphan branch firing when ARGUS has
  no `_managed_positions[symbol]` but broker reports non-zero position.
- Broker-orphan SHORT → `SystemAlertEvent(severity="critical",
  source="reconciliation", alert_type="phantom_short", symbol=symbol,
  shares=N, side=OrderSide.SELL)`.
- Broker-orphan LONG cycle 1–2 → WARNING log only.
- Broker-orphan LONG cycle ≥3 → `SystemAlertEvent(severity="warning",
  alert_type="stranded_broker_long", ...)` with exponential-backoff
  re-alert (3 → 6 → 12 → 24 cycles, capped at hourly per M2).
- `_broker_orphan_long_cycles: dict[str, int]` cleared on broker-zero
  observation; reset on session start.

Side-aware reads (2b.2 — **four count-filter sites + one alert-alignment
site**, two distinct patterns per third-pass HIGH #2):

**Pattern A: Side-aware count filter** (apply long-only filter; phantom
shorts don't inflate counts that drive safety decisions):
- **Margin circuit reset count** (`order_manager.py:1492` area):
  `len([p for p in broker_positions if p.side == OrderSide.BUY])`. Log
  breakdown: "Margin circuit reset check: longs=N, shorts=M,
  reset_threshold=K, will_reset=...".
- **Risk Manager max-concurrent-positions site #1** (`risk_manager.py:335`):
  same long-only filter pattern. Log breakdown.
- **Risk Manager max-concurrent-positions site #2** (`risk_manager.py:771`):
  same long-only filter pattern. Log breakdown.
- **Health daily integrity check** (`health.py:443-450`): iterate
  positions side-aware. Long-orphans without stops continue to emit
  the existing "Integrity Check FAILED" alert. Shorts (which by
  construction should not exist in ARGUS's long-only model) emit
  `phantom_short` alert via the same taxonomy and are excluded from
  the missing-stop count.

**Pattern B: Alert taxonomy alignment** (no filter; existing detection
gets additional alert emission for taxonomy consistency):
- **EOD Pass 2 short detection** (`order_manager.py:~1734`): existing
  `logger.error` log line preserved. NEW: emit
  `SystemAlertEvent(alert_type="phantom_short",
  source="eod_flatten", ...)` so the `phantom_short` alert taxonomy is
  consistent across detection sites (reconciliation orphan branch,
  Health integrity check, EOD Pass 2). No behavioral change to detection
  itself — the change is observability.

Per-symbol entry gate (2c.1 + 2c.2):
- `_phantom_short_gated_symbols: set[str]` state.
- `OrderApprovedEvent` handler rejects with
  `phantom_short_gate` reason for gated symbols. Per-symbol
  granularity: gating symbol X does not affect signals for symbol Y.
- **SQLite persistence (M5):** state persists to
  `data/operations.db` `phantom_short_gated_symbols` table.
  Rehydrated on startup BEFORE OrderManager begins processing
  `OrderApprovedEvent` (closes 60s window of unsafe entries on
  restart).
- Auto-clear after **5 consecutive zero-shares cycles** (was 3; per
  M4 cost-of-error asymmetry).

Operator override + observability (2d):
- `POST /api/v1/reconciliation/phantom-short-gate/clear` endpoint
  with `{symbol, reason}` body, audit-log entry per M3 schema.
- Audit-log table `phantom_short_override_audit` in
  `data/operations.db` with full schema:
  `(timestamp_utc, timestamp_et, symbol, prior_engagement_source,
  prior_engagement_alert_id, reason_text, override_payload_json)`.
  Persists across restarts.
- CRITICAL startup log line listing all gated symbols + runbook
  pointer.
- **Always fire one aggregate alert + always fire per-symbol alerts**
  (no suppression per L3). When ≥`phantom_short_aggregate_alert_threshold`
  symbols gated at startup, the aggregate `phantom_short_startup_engaged`
  alert fires alongside the individual alerts. **Threshold is
  configurable** (per third-pass LOW #15) via
  `reconciliation.phantom_short_aggregate_alert_threshold: 10` (default).
- `docs/live-operations.md` runbook section.

Config:
- `reconciliation.broker_orphan_alert_enabled: true` (default)
- `reconciliation.broker_orphan_entry_gate_enabled: true` (default)
- `reconciliation.broker_orphan_consecutive_clear_threshold: 5`
  (was 3)
- `reconciliation.phantom_short_aggregate_alert_threshold: 10`
  (default; configurable per LOW #15)

#### D6 — Side-aware DEF-158 retry path (Session 3)

`_check_flatten_pending_timeouts` at `order_manager.py:2384` reads
`getattr(bp, "side", None)` alongside `bp.shares`. 3-branch logic
mirrors IMPROMPTU-04:

- `side == OrderSide.BUY` and `broker_qty > 0` → flatten as today.
- `side == OrderSide.SELL` → CRITICAL log "Flatten retry refused:
  broker is short, ARGUS thought long — investigate via
  `scripts/ibkr_close_all_positions.py`", emit
  `SystemAlertEvent(alert_type="phantom_short_retry_blocked",
  severity="critical")`, do NOT issue SELL, clear flatten-pending.
- `side` None or unrecognized → ERROR log, do NOT issue SELL, clear
  flatten-pending.

Existing qty-mismatch and broker_qty == 0 branches preserve behavior.

#### D7 — Mass-balance categorized variance script + IMSR replay (Session 4)

- `scripts/validate_session_oca_mass_balance.py` consumes
  `logs/argus_YYYYMMDD.jsonl` and produces a categorized variance
  report per the H2 disposition:
  - `expected_partial_fill` rows (no flag)
  - `eventual_consistency_lag` rows (no flag)
  - `unaccounted_leak` rows (flag, exit non-zero)
  Returns exit code 0 if no `unaccounted_leak` rows, exit 1 otherwise.
- IMSR replay test (`tests/integration/test_imsr_replay.py`): consumes
  `logs/argus_20260424.jsonl` (operator-confirmed available); replays
  through BacktestEngine harness with post-fix code; asserts IMSR EOD
  position is 0 (not −200). **No synthetic-recreation fallback** (per
  H4 disposition).
- `docs/pre-live-transition-checklist.md` updated with **decomposed
  live-enable gate criteria** (per third-pass HIGH #4):
  1. ≥3 paper sessions with zero `unaccounted_leak` mass-balance rows
  2. AND zero `phantom_short` alerts across those sessions
  3. **(3a) Pre-live paper stress test:** ≥1 paper-trading session
     under live-config simulation (paper-trading data-capture
     overrides removed; risk limits restored to production values;
     overflow capacity restored; ≥10 entries placed during the
     session); zero `phantom_short` alerts; zero `unaccounted_leak`
     mass-balance rows
  4. **(3b) Live rollback policy:** First live trading session caps
     position size at **$50–$500 notional** on a single
     operator-selected symbol. Any `phantom_short*` or
     `phantom_short_retry_blocked` alert during the window triggers
     immediate suspension via operator-manual halt (formal
     `POST /api/v1/system/suspend` deferred — DEF-210). After
     session-end clean, expand to standard sizing on day 2.
- **Spike script trigger registry** added to
  `docs/live-operations.md` (per third-pass HIGH #5):
  re-run `scripts/spike_ibkr_oca_late_add.py` before any live-trading
  transition; before/after any `ib_async` library version upgrade;
  before/after any IBKR API version change (TWS/Gateway upgrade);
  monthly during paper-trading windows. Failure to return
  `PATH_1_SAFE` invalidates the OCA-architecture seal and triggers
  Tier 3 review. Spike result file (`spike-results-YYYYMMDD.json`)
  must be dated within the last 30 days when in paper-trading mode.
- `docs/protocols/market-session-debrief.md` Phase 7 gains the
  bracket-stop slippage watch item per D8 acceptance.

#### D8 — Performance Considerations + restart-required rollback (in Sprint Spec)

Spec includes Performance Considerations section explaining the
ocaType=1 50–200ms cancellation propagation cost on cancelling
siblings. Architectural justification for ocaType=1 over ocaType=2.

**Reverse-rollback escape hatch is RESTART-REQUIRED** (H1):
`bracket_oca_type: 0` flip requires operator restart so all in-flight
positions reconstruct under new config. Mid-session flip explicitly
unsupported. Documented in `docs/live-operations.md` runbook.

Post-merge slippage debrief check (Session 4): mean bracket-stop fill
slippage degrades by ≤$0.02 on $7–15 share universe vs pre-31.91
baseline. Threshold breach triggers restart-required rollback
evaluation.

#### D9a — HealthMonitor consumer + REST endpoints + acknowledgment flow (Session 5a.1)

**Backend half-1 of alert observability** (per third-pass HIGH #1 split):

**HealthMonitor consumer expansion:** `argus/core/health.py`
`HealthMonitor` subscribes to `SystemAlertEvent` from the Event Bus.
Maintains active-alert state in-memory. Tracks alert lifecycle:
`active` → `acknowledged` → (auto-resolved on condition-cleared) →
`archived`.

**REST endpoint:** `GET /api/v1/alerts/active` returns current
active-alert state (initial-load for frontend, fallback for WebSocket
disconnect recovery). `GET /api/v1/alerts/history?since=<ts>` returns
historical alerts within window.

**Acknowledgment flow with atomic transitions and idempotency** (per
third-pass MEDIUM #10):
- `POST /api/v1/alerts/{alert_id}/acknowledge` with `{reason,
  operator_id}` body
- **Atomic transition:** alert state change AND audit-log write happen
  in a single SQLite transaction; any failure rolls back both
- **Idempotency:**
  - 200 if already acknowledged (returns original acknowledger info;
    still writes audit-log row capturing the duplicate-ack attempt)
  - 404 if alert ID unknown (no audit-log row)
  - 409 if alert auto-resolved before acknowledge (still writes
    audit-log row capturing the late-ack attempt)
- **Race resolution:** first writer wins; second sees 409
- **No-operator case:** critical alerts never auto-acknowledge but
  auto-resolve on condition-cleared (default policy); `audit_log` row
  for `auto_resolution` includes `operator_id="auto"`

**`AlertsConfig` Pydantic model** (NEW): `acknowledgment_required_severities:
list[str] = ["critical"]`.

#### D9b — WebSocket fan-out + persistence + auto-resolution policy + retention (Session 5a.2)

**Backend half-2 of alert observability** (per third-pass HIGH #1 split):

**WebSocket fan-out:** new endpoint `WS /ws/v1/alerts` fans out alert
state changes (new alert, acknowledgment, auto-resolution) to
connected clients in real-time. Pattern mirrors existing `/ws/v1/arena`
and `/ws/v1/observatory`.

**SQLite persistence + restart recovery:** alert state persists to
`alert_state` table in `data/operations.db`. On restart, HealthMonitor
rehydrates alert state from SQLite BEFORE event bus subscription
becomes active.

**Auto-resolution policy table** (per third-pass HIGH #1 — explicit
per-alert-type):

| Alert type | Auto-resolution condition | Operator ack required? |
|---|---|---|
| `phantom_short` | 5 cycles zero-shares for symbol (matches 2c.2 gate clear-threshold) | No (auto-resolves) |
| `stranded_broker_long` | broker reports zero for symbol | No (auto-resolves) |
| `phantom_short_retry_blocked` | NEVER auto-resolves | **Yes** (ack required) |
| `cancel_propagation_timeout` | NEVER auto-resolves (one-shot critical) | **Yes** (ack required) |
| `ibkr_disconnect` | successful subsequent IBKR operation | No (auto-resolves) |
| `ibkr_auth_failure` | successful subsequent IBKR-authenticated operation | No (auto-resolves) |
| `databento_dead_feed` | 3 healthy heartbeats | No (auto-resolves) |
| `phantom_short_startup_engaged` (aggregate alert) | all engaged symbols cleared OR 24h elapsed | **Yes** (ack required for 24h auto-archive) |

**Retention policy and VACUUM** (per third-pass MEDIUM #9):
- `phantom_short_override_audit` and `alert_acknowledgment_audit`
  tables: retain forever (forensic; configurable via
  `audit_log_retention_days: int | None = None`)
- `phantom_short_gated_symbols` table: current-state, no retention
  (cleared on auto-clear or operator override)
- `alert_state` table: archived alerts pruned after 90 days
  (`archived_alert_retention_days: int = 90`)
- VACUUM strategy: scheduled VACUUM via `asyncio.to_thread` mirroring
  the Sprint 31.8 S2 evaluation.db pattern (close → sync VACUUM → reopen)
- **Schema-version table + migration registry** in `data/operations.db`
  (NEW per MEDIUM #9; first migration framework in ARGUS — even one
  migration justifies the framework before the next sprint adds another
  table)

**Auto-resolution implementation:**
- Subscribers maintain per-alert-type "cleared-condition" predicates
- Predicates evaluated on every relevant Event Bus event (e.g.,
  `ReconciliationCompletedEvent` for phantom_short)
- When predicate fires: alert auto-marked `archived`; WebSocket pushes
  state change; audit-log row captures auto-resolution

**Config (additions to AlertsConfig):**
- `auto_resolve_on_condition_cleared: bool = True`
- `audit_log_retention_days: int | None = None` (forever by default)
- `archived_alert_retention_days: int = 90`

#### D10 — IBKR emitter TODO resolution + end-to-end integration tests (Session 5b)

Resolve the two pre-existing IBKR emitter TODO sites:

- `argus/execution/ibkr_broker.py:453` — emit `SystemAlertEvent` on
  IBKR Gateway disconnect / reconnect failure (currently TODO comment
  only)
- `argus/execution/ibkr_broker.py:531` — emit `SystemAlertEvent` on
  IBKR API authentication / permission failure (currently TODO)

**Alpaca emitter TODO** (`argus/data/alpaca_data_service.py:593`)
**EXPLICITLY EXCLUDED** from this sprint — gets resolved by deletion
in Sprint 31.94.

**Behavioral anti-regression assertion** (per third-pass MEDIUM #13;
replaces the earlier line-number-based textual check which was
brittle to innocuous edits):

```python
def test_alpaca_data_service_does_not_emit_system_alert_events():
    """Sprint 31.91 boundary: Alpaca emitter site stays unwired
    until Sprint 31.94 retires the broker by deletion."""
    import inspect
    import argus.data.alpaca_data_service as mod
    src = inspect.getsource(mod)
    assert "SystemAlertEvent" not in src, (
        "Alpaca data service should not emit SystemAlertEvent — "
        "queued for retirement in Sprint 31.94 (DEF-178/183)."
    )
```

Robust to refactors; enforces the actual constraint (no emission); has
a clear failure message pointing to the rationale.

End-to-end integration tests assert:
- Emit (any of: Databento dead feed, IBKR disconnect, IBKR auth
  failure, phantom_short detection)
- → HealthMonitor consume
- → REST exposure (assertable via `GET /api/v1/alerts/active`)
- → WebSocket push (assertable via test WebSocket client)
- → Operator acknowledgment via REST POST
- → Audit-log persistence
- → Auto-resolution on condition-cleared (per the policy table in D9b)

#### D11 — Frontend `useAlerts` hook + Dashboard banner (Session 5c)

`frontend/src/hooks/useAlerts.ts` new TanStack Query / WebSocket hybrid
hook:
- Initial state via `GET /api/v1/alerts/active` (TanStack Query
  cache)
- Real-time updates via WebSocket subscription to `/ws/v1/alerts`
- Reconnect resilience: on WebSocket disconnect, falls back to
  TanStack Query polling; on reconnect, refetches state via REST and
  resumes WebSocket
- Pattern mirrors existing `useObservatory` and `useArena` hooks

`frontend/src/components/AlertBanner.tsx` new component:
- Persistent banner at top of Dashboard for ANY active critical alert
- Severity-coded styling (critical = red, warning = yellow)
- Acknowledgment button → calls
  `POST /api/v1/alerts/{alert_id}/acknowledge`
- Disappears within 1s of acknowledgment OR auto-resolution

Vitest tests cover hook state machine, banner rendering, acknowledgment
flow, severity styling, WebSocket reconnect behavior.

#### D12 — Toast notification system + acknowledgment UI flow (Session 5d)

`frontend/src/components/AlertToast.tsx` new component:
- Pops up on ANY page when a new critical alert arrives via WebSocket
- Persists until acknowledged or auto-dismissed on
  condition-cleared
- Click-to-acknowledge opens
  `AlertAcknowledgmentModal` for reason entry

`frontend/src/components/AlertAcknowledgmentModal.tsx` new component:
- Modal dialog requiring reason text before acknowledgment
- Posts to `POST /api/v1/alerts/{alert_id}/acknowledge` with reason
- Shows audit-log entry on success
- Cancellable (alert stays active)

Toasts queue if multiple critical alerts arrive simultaneously
(stacked, oldest-first dismissed when queue >5).

Vitest tests cover toast appearance, queue behavior, modal flow,
acknowledgment submission, error handling.

#### D13 — Observatory alerts panel + cross-page integration (Session 5e)

`frontend/src/pages/Observatory.tsx` gains an alerts panel:
- Active alerts (sortable, filterable by severity / source / symbol)
- Historical alerts (with date-range picker)
- Acknowledgment audit trail visible per alert
- Click-through to detailed alert view with full event payload

**Cross-page integration:** `frontend/src/components/Layout.tsx` mounts
`AlertBanner` at the layout level so it's visible across all 10 pages,
not just Dashboard. `AlertToast` system also at layout level so toasts
appear regardless of current page.

Banner persistence assertion (regression invariant 17): banner remains
visible when navigating between Command Center pages while a critical
alert is active.

Vitest + integration tests cover Observatory panel rendering, sort /
filter, banner cross-page persistence, toast cross-page behavior.

#### D14 — DEF-014 closure documentation (sprint-close, doc-sync)

`CLAUDE.md` DEF table marks DEF-014 as CLOSED with citation to Sprint
31.91 + Sessions 5a–5e + DEC-388 (alert observability decision, to be
filed). Architecture doc gains §14 (alert observability) describing
the HealthMonitor consumer + WebSocket fan-out + REST endpoint
architecture as a reference pattern for future emitters.

### Acceptance Criteria

#### AC for D1 — `cancel_all_orders(symbol, await_propagation)` API

- Default behavior (no args, or `symbol=None`, `await_propagation=False`)
  preserves DEC-364 contract.
- With `symbol="AAPL"`, only AAPL's working orders are cancelled.
- With `await_propagation=True`, function does not return until broker
  reports zero working orders for the filtered scope (or 2s timeout
  fires with `CancelPropagationTimeout` exception).
- All 3 implementations pass the new contract tests.
- AlpacaBroker raises `DeprecationWarning` when invoked (not exercised
  in any other test path).
- Anti-regression: existing `cancel_all_orders()` tests pass unchanged.

#### AC for D2 — Bracket OCA grouping + Error 201 defensive

- Bracket children carry `ocaGroup == oca_group_id` and `ocaType == 1`.
- `oca_group_id = f"oca_{parent_ulid}"` (deterministic derivation per
  M1).
- `ManagedPosition.oca_group_id: str | None` field added.
- Re-entry on same symbol generates new `oca_group_id`.
- `bracket_oca_type` config accepts only 0 or 1.
- DEC-117 rollback test with ocaType=1 cancels OCA siblings.
- **NEW (Error 201 defensive):** test that simulates Error 201
  "OCA group is already filled" on T1/T2 placement; asserts logged
  INFO; asserts rollback path fires; asserts no orphaned OCA-A working
  orders.

#### AC for D3 — Standalone-SELL OCA threading + Error 201 graceful

- All 4 SELL paths thread `oca_group_id` when set.
- All 4 paths fall through to no-OCA behavior when
  `oca_group_id is None`.
- Grep regression guard in place.
- **NEW (Error 201 graceful):** test that simulates Error 201
  "OCA group is already filled" on standalone-SELL placement; asserts
  logged INFO not ERROR; asserts ManagedPosition marked "redundant
  exit"; asserts DEF-158 retry path NOT triggered.
- Distinguishing test: generic Error 201 (margin) still treated as
  ERROR with retry; OCA-filled Error 201 treated as SAFE.

#### AC for D4 — Broker-only paths safety + reconstruct docstring

- All 3 functions invoke
  `cancel_all_orders(symbol=..., await_propagation=True)` BEFORE SELL
  placement.
- Cancellation timeout (2s) raises `CancelPropagationTimeout`; SELL is
  aborted; `cancel_propagation_timeout` alert emitted.
- `reconstruct_from_broker()` cancels per-symbol BEFORE wiring into
  `_managed_positions`.
- **NEW:** docstring on `reconstruct_from_broker()` documents the
  startup-only contract and the requirement for future callers to add
  context-awareness.

#### AC for D5 — Side-aware reconciliation (covers 2a + 2b.1 + 2b.2 + 2c.1 + 2c.2 + 2d)

- `ReconciliationPosition` frozen dataclass.
- `reconcile_positions` signature accepts typed dict.
- Broker-orphan SHORT → `phantom_short` alert.
- Broker-orphan LONG cycle 1–2 → WARNING.
- Broker-orphan LONG cycle ≥3 → `stranded_broker_long` alert with
  exponential-backoff re-alert.
- **Three-site B5 fix:** Margin circuit reset uses long-only count
  AND Risk Manager max-concurrent-positions uses long-only count AND
  Health integrity check side-aware. All log breakdown lines.
- Per-symbol entry gate auto-clears after 5 cycles (default; was 3).
- Gate state persists to SQLite; rehydrates on startup BEFORE event
  processing.
- Operator override API endpoint with full audit-log schema (M3).
- Always fire aggregate + individual alerts (L3 — no suppression).
- CRITICAL startup log line lists all gated symbols.

#### AC for D6 — DEF-158 retry side-check

- 3-branch logic applied; BUY preserves existing behavior.
- SELL branch: no SELL placed; `phantom_short_retry_blocked` alert
  with severity critical; pending cleared.
- Unknown branch: no SELL; ERROR log; pending cleared.

#### AC for D7 — Mass-balance + IMSR replay

- `scripts/validate_session_oca_mass_balance.py` produces categorized
  variance report; exits 0 only if zero `unaccounted_leak` rows.
- `expected_partial_fill` and `eventual_consistency_lag` categorized
  per H2 definitions; documented in script docstring.
- IMSR replay test uses `logs/argus_20260424.jsonl` directly; asserts
  IMSR EOD position is 0.
- `pre-live-transition-checklist.md` lists 3 live-enable gate
  criteria.
- `market-session-debrief.md` Phase 7 has slippage watch item.

#### AC for D8 — Performance Considerations + restart-required rollback

- Sprint Spec includes Performance Considerations section (this
  document, above).
- Architectural justification for ocaType=1 vs 2 documented.
- Restart-required rollback documented in `live-operations.md`.
- Post-merge slippage debrief check delivered.

#### AC for D9a — HealthMonitor + REST + acknowledgment (Session 5a.1)

- `HealthMonitor` subscribes to `SystemAlertEvent` and maintains
  alert state (in-memory).
- `GET /api/v1/alerts/active` returns current state.
- `GET /api/v1/alerts/history?since=...` returns historical alerts.
- `POST /api/v1/alerts/{alert_id}/acknowledge` writes audit-log entry
  and returns updated state.
- **Atomic transition** (per MEDIUM #10): alert state change AND audit-log
  write happen in a single SQLite transaction; failure rolls back both.
- **Idempotency** (per MEDIUM #10): 200 if already acked (returns
  original acknowledger info; still writes duplicate-ack audit row);
  404 if alert ID unknown; 409 if alert auto-resolved before
  acknowledge (still writes late-ack audit row).
- **Race resolution**: first writer wins; second sees 409.
- `AlertsConfig` Pydantic model loadable from YAML with default
  `acknowledgment_required_severities: ["critical"]`.

#### AC for D9b — WebSocket + persistence + auto-resolution + retention (Session 5a.2)

- `WS /ws/v1/alerts` pushes state changes (new alert, acknowledgment,
  auto-resolution) in real-time to connected clients.
- `alert_state` SQLite table persists active + archived alerts; survives
  restart; HealthMonitor rehydrates state BEFORE Event Bus subscription
  becomes active.
- Audit-log entries (`alert_acknowledgment_audit` table) survive
  restart with full payload (alert_id, operator_id, timestamp, reason,
  prior state).
- **Auto-resolution policy table** (per HIGH #1) implemented as
  per-alert-type predicates evaluated on relevant Event Bus events:
  - `phantom_short` → 5 cycles zero-shares (config-aligned with 2c.2)
  - `stranded_broker_long` → broker reports zero
  - `phantom_short_retry_blocked` → never auto (operator ack required)
  - `cancel_propagation_timeout` → never auto (operator ack required)
  - `ibkr_disconnect`/`ibkr_auth_failure` → successful subsequent op
  - `databento_dead_feed` → 3 healthy heartbeats
  - `phantom_short_startup_engaged` (aggregate) → all engaged cleared OR
    24h elapsed (operator ack required for 24h auto-archive)
- **Retention policy** (per MEDIUM #9) — audit logs forever (configurable
  via `audit_log_retention_days: int | None = None`); current-state
  tables no retention; `alert_state` archived rows pruned after 90 days
  (configurable via `archived_alert_retention_days: int = 90`).
- **VACUUM strategy** for `data/operations.db` mirrors Sprint 31.8 S2
  evaluation.db pattern (close → sync VACUUM via `asyncio.to_thread` →
  reopen).
- **Schema-version table + migration registry** in `data/operations.db`;
  first migration loads under the new framework; framework documented
  for future schema changes.

#### AC for D10 — IBKR emitters + E2E

- `ibkr_broker.py:453` and `:531` TODO sites resolved with
  `SystemAlertEvent` emissions.
- Alpaca emitter site explicitly NOT touched.
- **Behavioral anti-regression assertion** (per MEDIUM #13) replaces
  brittle line-number-based textual check:
  `inspect.getsource(alpaca_data_service)` must not contain
  `"SystemAlertEvent"`. Robust to refactors.
- End-to-end integration tests assert full pipeline
  (emit → consume → REST → WebSocket → ack → audit → auto-resolution).
- All 4+ emitter sites (Databento, IBKR×2, phantom_short×4 from
  Sessions 2b/3) tested via E2E.

#### AC for D11 — Frontend `useAlerts` + banner

- Hook fetches initial state via REST.
- Hook subscribes to WebSocket.
- Hook handles disconnect by falling back to polling.
- Hook handles reconnect by refetching + resubscribing.
- `AlertBanner` renders for any active critical alert.
- Acknowledgment button posts to REST.
- Banner disappears on acknowledgment OR auto-resolution.
- Vitest coverage of state machine and rendering.

#### AC for D12 — Toast + acknowledgment UI

- `AlertToast` appears on any page when new critical alert arrives.
- Toast persists until acknowledged or auto-dismissed.
- Click opens `AlertAcknowledgmentModal`.
- Modal requires reason text.
- Successful acknowledgment shows audit-log entry.
- Toast queue handles multiple alerts (stacked).
- Vitest coverage.

#### AC for D13 — Observatory panel + cross-page integration

- Observatory page has alerts panel with active + historical views.
- Sort / filter functional.
- Acknowledgment audit trail visible per alert.
- `AlertBanner` mounted at Layout level (visible all 10 pages).
- `AlertToast` mounted at Layout level.
- Banner cross-page persistence asserted via Vitest test.
- Toast cross-page behavior asserted.

#### AC for D14 — DEF-014 closure

- DEF-014 marked CLOSED in CLAUDE.md DEF table.
- Architecture doc §14 added describing alert observability.
- DEC-388 (alert observability) filed in decision-log.

### Performance Considerations

(See `design-summary.md` §"Performance Considerations" for the full
text. Summary: ocaType=1 adds 50–200ms fill-latency on cancelling
siblings; trade-off accepted; ocaType=2 architecturally wrong for
ARGUS; restart-required rollback escape hatch documented.)

### Mass-Balance + IMSR Replay (revised acceptance)

(See `design-summary.md` §"Mass-Balance + IMSR Replay". Summary:
categorized variance per H2; Apr 24 `.jsonl` direct replay per H4;
spike script committed as live-IBKR regression check.)

### Config Changes

(See `design-summary.md` §"Config Changes" — 6 fields added across
Sessions 1a, 2b.1, 2c.1, 2c.2, 5a×2.)

## Dependencies

- Sprint folder rename completed (already done).
- **Phase C-1 third-pass adversarial review** cleared on revised
  artifacts.
- DEF-204 still OPEN in CLAUDE.md at sprint start.
- Operator daily flatten mitigation in effect throughout 7–8 week
  window.
- `ib_async` `ocaGroup` / `ocaType` field support verified.
- **Apr 24 paper-session log confirmed at
  `logs/argus_20260424.jsonl`** (operator confirmed).
- **OCA late-add spike result `PATH_1_SAFE` confirmed**
  (2026-04-27).
- `main` HEAD on a known-green CI commit at session start.
- Adversarial Tier 2 reviewer engaged for all 18 sessions.
- Tier 3 reviewer engaged after Session 1c lands (review #1) and
  after Session 5b lands (review #2).
- **Frontend reviewer arrangements confirmed for Sessions 5c–5e.**

## Relevant Decisions

Unchanged from prior plus:

- **DEC-385 reserved** — Side-aware reconciliation contract. Now spans
  6 sessions (2a / 2b.1 / 2b.2 / 2c.1 / 2c.2 / 2d).
- **DEC-386 reserved** — OCA-group threading + broker-only safety. Now
  spans 4 sessions (0 / 1a / 1b / 1c).
- **DEC-388 reserved** — Alert observability architecture
  (HealthMonitor consumer + WebSocket fan-out + REST endpoint +
  acknowledgment flow). Resolves DEF-014. Spans **6 sessions** (5a.1 /
  5a.2 / 5b / 5c / 5d / 5e) — was 5 before third-pass HIGH #1 split.

## Relevant Risks

Unchanged from prior plus:

- **DEC-117 + Error 201/OCA-filled handling** must NOT conflate
  generic Error 201 (margin, etc.) with OCA-filled. Distinguishing
  test required.
- **WebSocket fan-out reconnect resilience** must handle the disconnect
  + REST recovery path correctly. Regression invariant 18.
- **Frontend banner cross-page persistence** must hold under
  navigation. Regression invariant 17.
- **Compaction risk:** Session 2a at ~10.5 is the highest score across
  the 18 sessions (after the 3rd-pass HIGH #1 split of 5a → 5a.1 + 5a.2
  brought 5a's prior score of ~12 down to 5a.1 ~8 + 5a.2 ~9). Watch
  threshold during pre-flight on 2a; consider mid-session split if mock
  updates exceed estimates (per LOW #16 — Session 2a pre-flight grep).

## Session Count Estimate

**18 sessions** estimated (was 17 after 2nd revision; was 12 after Phase
A; was 10 first revision; was 6 originally):

| Session | Compaction score (preliminary) |
|---|---:|
| 0 — `cancel_all_orders` API | ~7 |
| 1a — Bracket OCA + Error 201 defensive | ~9.5 |
| 1b — Standalone-SELL OCA + Error 201 graceful | ~9 |
| 1c — Broker-only paths safety + docstring | ~9 |
| 2a — Reconciliation contract refactor | ~10.5 |
| 2b.1 — Broker-orphan + alert + cycle infra | ~8 |
| 2b.2 — Four count-filter sites + one alert-alignment | ~10 |
| 2c.1 — Gate state + handler + persistence | ~9 |
| 2c.2 — Clear-threshold (default 5) | ~6 |
| 2d — Override API + audit + always-both-alerts + configurable threshold | ~9 |
| 3 — DEF-158 retry side-check | ~6 |
| 4 — Mass-balance + IMSR replay | ~7 |
| **5a.1 — HealthMonitor consumer + REST + acknowledgment (atomic + idempotent)** | **~8** |
| **5a.2 — WebSocket + persistence + auto-resolution policy + retention/migration** | **~9** |
| 5b — IBKR emitters + E2E + behavioral Alpaca check | ~9 |
| 5c — `useAlerts` hook + banner | ~9 |
| 5d — Toast + ack UI | ~8 |
| 5e — Observatory panel + cross-page | ~8 |

Sequential execution required. Sprint duration: 7–8 weeks. Highest
session-level compaction score: 2a at ~10.5 (well under 14 threshold).
The 5a split brings the prior highest score (5a at ~12) under the
threshold even with full per-alert-type auto-resolution policy + retention
policy + migration framework loaded into 5a.2.

---

*End Sprint 31.91 Sprint Spec (revised 3rd pass — 18-session shape).*
