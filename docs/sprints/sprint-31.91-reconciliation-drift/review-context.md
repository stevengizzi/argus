# Sprint 31.91 — Tier 2 Review Context

> **Phase D artifact (shared).** This is the single backing file referenced
> by every Tier 2 session review prompt in Sprint 31.91. It contains the
> full Sprint Spec, Specification by Contradiction, Sprint-Level Regression
> Checklist, and Sprint-Level Escalation Criteria embedded inline so the
> @reviewer subagent can read this one file plus the session close-out and
> have everything needed to verdict.
>
> **Do NOT modify this file during sprint execution.** It freezes the
> Phase C-1 third-pass-cleared spec. If a session discovers a spec gap,
> file the discovery in the work-journal conversation, not here.
>
> **Sprint:** 31.91 — Reconciliation Drift (DEF-204 fix + DEF-014 resolution)
> **Predecessor:** Sprint 31.9 (Health & Hardening campaign-close, sealed 2026-04-24)
> **Sessions:** 0, 1a, 1b, 1c, 2a, 2b.1, 2b.2, 2c.1, 2c.2, 2d, 3, 4, 5a.1, 5a.2, 5b, 5c, 5d, 5e (18)
> **Mode:** Human-in-the-loop. Working on `main`.
> **Mitigation in effect:** Operator runs `scripts/ibkr_close_all_positions.py` daily until DEF-204 lands.
> **Tier 3 reviews:** After Session 1c (combined diff 0+1a+1b+1c) and after Session 5b (combined diff 5a.1+5a.2+5b).

---

## Review Instructions

You are conducting a Tier 2 code review for one session of Sprint 31.91.

**This is a READ-ONLY session.** Do NOT modify any source code files. The
ONE permitted write is the review report file itself
(`docs/sprints/sprint-31.91-reconciliation-drift/session-{M}-review.md`),
including a structured JSON verdict appendix fenced with
` ```json:structured-verdict ` per the review skill.

Follow the review skill in `.claude/skills/review.md`.

**Read `.claude/rules/universal.md` in full and treat its contents as
binding for this review.** RULE-013 (read-only mode) governs the
entire review session. RULE-038 (grep-verify discipline) and RULE-050
(CI must be green) are particularly relevant for this sprint.

**Your verdict must be one of:**
- `CLEAR` — proceed to next session.
- `CONCERNS` — medium issues that need triage. The implementation session
  may iterate within itself per the Post-Review Fix Documentation pattern;
  if so, the verdict transitions to `CONCERNS_RESOLVED` after fixes land.
- `ESCALATE` — requires operator. Do NOT fix without human review.

The implementation prompt's @reviewer invocation at session-end provides:
1. This review context file (the `review-context.md` you just opened)
2. The session close-out report path
3. The diff range (`git diff HEAD~1` typically)
4. The test command to run
5. The list of files that should NOT have been modified

**Critical sprint-wide invariants — verify on every session:**
1. DEF-199 A1 fix at `argus/execution/order_manager.py:1670-1750` — zero
   edits. Pattern detection: `git diff HEAD~1 -- argus/execution/order_manager.py`
   inspected for line-range overlap.
2. IMPROMPTU-04 startup invariant region in `argus/main.py` — zero edits
   except the scoped exceptions documented in regression invariant 15
   (Session 1c reconstruct body, Session 2a reconcile call site at
   `:1505-1535`, Session 2c.1 startup gate-state rehydration, Session 5a.1
   HealthMonitor consumer init).
3. Pre-existing 5,080 pytest baseline holds; new tests are additive only.
4. Pre-existing flake count (DEF-150, DEF-167, DEF-171, DEF-190, DEF-192)
   does not regress (RULE-041).
5. CI must be green on the session's final commit (RULE-050).

The full 22-invariant list is embedded below as the
**Sprint-Level Regression Checklist**.

---

# Embedded: Sprint Spec

> Source: `sprint-spec.md` (Phase C-1 third-pass cleared, 2026-04-27).

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

## Deliverables (14 across 18 sessions)

### D1 — `Broker.cancel_all_orders(symbol, await_propagation)` API extension (Session 0)

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

### D2 — Bracket OCA grouping + Error 201 defensive handling (Session 1a)

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

### D3 — Standalone-SELL OCA threading + Error 201 graceful handling (Session 1b)

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

### D4 — Broker-only SELL paths safety + reconstruct docstring (Session 1c)

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

**Failure-mode change for EOD Pass 2** (Item 2 disposition): prior
behavior placed the SELL unconditionally; Session 1c gates SELL
placement on successful `cancel_all_orders(symbol,
await_propagation=True)`. On 2s cancel-timeout: the SELL is aborted,
`cancel_propagation_timeout` alert fires, and the position remains
at the broker as a phantom long with no working stop. This is the
intended trade-off — incorrect SELLs were the bug we're fixing
(phantom shorts compound risk); leaked longs are exposure-with-stop-of-zero
(also bad, but bounded by the underlying long position size, vs.
phantom shorts which create unbounded short exposure). Operator
response: when `cancel_propagation_timeout` alert fires for an
EOD-flatten path symbol, manually flatten via
`scripts/ibkr_close_all_positions.py` before the next session begins.

### D5 — Side-aware reconciliation contract (Sessions 2a + 2b.1 + 2b.2 + 2c.1 + 2c.2 + 2d)

**Contract refactor (2a):**
- `OrderManager.reconcile_positions()` accepts
  `dict[str, ReconciliationPosition]` (frozen dataclass: `symbol`,
  `side`, `shares`) instead of `dict[str, float]`.
- Call site in `argus/main.py:1505-1535` updated.

**Detection + alerts (2b.1):**
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

**Side-aware reads (2b.2 — four count-filter sites + one alert-alignment site, two distinct patterns per HIGH #2):**

**Pattern A: Side-aware count filter** (apply long-only filter; phantom
shorts don't inflate counts that drive safety decisions):
- Margin circuit reset count (`order_manager.py:1492` area):
  `len([p for p in broker_positions if p.side == OrderSide.BUY])`. Log
  breakdown.
- Risk Manager max-concurrent-positions site #1 (`risk_manager.py:335`):
  same long-only filter.
- Risk Manager max-concurrent-positions site #2 (`risk_manager.py:771`):
  same long-only filter.
- Health daily integrity check (`health.py:443-450`): iterate
  positions side-aware. Long-orphans without stops continue to emit
  the existing "Integrity Check FAILED" alert. Shorts emit
  `phantom_short` alert via the same taxonomy and are excluded from
  the missing-stop count.

**Pattern B: Alert taxonomy alignment** (no filter; existing detection
gets additional alert emission for taxonomy consistency):
- EOD Pass 2 short detection (`order_manager.py:~1734`): existing
  `logger.error` log line preserved. NEW: emit
  `SystemAlertEvent(alert_type="phantom_short",
  source="eod_flatten", ...)` so the `phantom_short` alert taxonomy is
  consistent across detection sites. No behavioral change to detection
  itself — the change is observability.

**Health + broker-orphan double-fire dedup (Item 3 disposition — operator chose Option C):** both alerts fire (preserves both safety signals at different cadences). Health check's alert message includes "see also: stranded_broker_long active since [ts]" so operator triages once and sees both contexts.

**Per-symbol entry gate (2c.1 + 2c.2):**
- `_phantom_short_gated_symbols: set[str]` state.
- `OrderApprovedEvent` handler rejects with `phantom_short_gate`
  reason for gated symbols. Per-symbol granularity.
- SQLite persistence (M5) to `data/operations.db`
  `phantom_short_gated_symbols` table. Rehydrated on startup BEFORE
  OrderManager begins processing `OrderApprovedEvent` (closes 60s
  window of unsafe entries on restart).
- Auto-clear after **5 consecutive zero-shares cycles** (was 3; per
  M4 cost-of-error asymmetry).

**Operator override + observability (2d):**
- `POST /api/v1/reconciliation/phantom-short-gate/clear` endpoint
  with `{symbol, reason}` body.
- Audit-log table `phantom_short_override_audit` in
  `data/operations.db` with full M3 schema:
  `(timestamp_utc, timestamp_et, symbol, prior_engagement_source,
  prior_engagement_alert_id, reason_text, override_payload_json)`.
- CRITICAL startup log line listing all gated symbols + runbook pointer.
- **Always fire one aggregate alert + always fire per-symbol alerts**
  (no suppression per L3). When ≥`phantom_short_aggregate_alert_threshold`
  symbols gated at startup, the aggregate `phantom_short_startup_engaged`
  alert fires alongside the individual alerts. Threshold is
  configurable via
  `reconciliation.phantom_short_aggregate_alert_threshold: 10` (default).
- `docs/live-operations.md` runbook section.

**Config additions:**
- `reconciliation.broker_orphan_alert_enabled: true` (default)
- `reconciliation.broker_orphan_entry_gate_enabled: true` (default)
- `reconciliation.broker_orphan_consecutive_clear_threshold: 5` (was 3)
- `reconciliation.phantom_short_aggregate_alert_threshold: 10`

### D6 — Side-aware DEF-158 retry path (Session 3)

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

### D7 — Mass-balance categorized variance script + IMSR replay (Session 4)

- `scripts/validate_session_oca_mass_balance.py` consumes
  `logs/argus_YYYYMMDD.jsonl` and produces a categorized variance
  report per the H2 disposition: `expected_partial_fill` (no flag),
  `eventual_consistency_lag` (no flag, ≤120s), `unaccounted_leak`
  (flag, exit non-zero). Returns exit 0 if no `unaccounted_leak`.
- IMSR replay test (`tests/integration/test_imsr_replay.py`): consumes
  `logs/argus_20260424.jsonl`; replays through BacktestEngine harness
  with post-fix code; asserts IMSR EOD position is 0 (not −200).
- `docs/pre-live-transition-checklist.md` updated with **decomposed
  live-enable gate criteria** (HIGH #4):
  1. ≥3 paper sessions with zero `unaccounted_leak` mass-balance rows
  2. AND zero `phantom_short` alerts across those sessions
  3. (3a) Pre-live paper stress test: ≥1 paper-trading session under
     live-config simulation; zero `phantom_short` alerts; zero
     `unaccounted_leak` mass-balance rows
  4. (3b) Live rollback policy: First live trading session caps
     position size at $50–$500 notional on a single operator-selected
     symbol. Any `phantom_short*` triggers operator-manual halt
     (formal `POST /api/v1/system/suspend` deferred — DEF-210).
- **Spike script trigger registry** in `docs/live-operations.md`
  (HIGH #5): re-run before live-trading transition; before/after
  `ib_async` upgrade; before/after IBKR API change; monthly during
  paper-trading windows. Spike result file must be dated within 30
  days when in paper-trading mode.
- **Spike script filename convention** standardized to ISO date with
  dashes (`spike-results-YYYY-MM-DD.json`) across script default,
  docstring, and regression invariant 22 date-parser (Item 7
  disposition).
- `docs/protocols/market-session-debrief.md` Phase 7 gains the
  bracket-stop slippage watch item per D8 acceptance.

### D8 — Performance Considerations + restart-required rollback

`ocaType=1` adds 50–200ms fill-latency on cancelling siblings (not
the firing order). This is the documented trade-off. ocaType=2
("Reduce with block") reduce-quantity semantics is architecturally
wrong for ARGUS's bracket model.

**Reverse-rollback escape hatch is RESTART-REQUIRED** (H1):
`bracket_oca_type: 0` flip requires operator restart so all in-flight
positions reconstruct under new config. Mid-session flip explicitly
unsupported. Documented in `docs/live-operations.md` runbook.

Post-merge slippage debrief check (Session 4): mean bracket-stop fill
slippage degrades by ≤$0.02 on $7–15 share universe vs pre-31.91
baseline.

### D9a — HealthMonitor consumer + REST endpoints + acknowledgment flow (Session 5a.1)

`HealthMonitor` subscribes to `SystemAlertEvent`. Maintains active-alert
state in-memory. Tracks `active` → `acknowledged` →
(auto-resolved on condition-cleared) → `archived`.

REST endpoints:
- `GET /api/v1/alerts/active` — current state
- `GET /api/v1/alerts/history?since=<ts>` — historical
- `POST /api/v1/alerts/{alert_id}/acknowledge` with `{reason, operator_id}` body

**Atomic transition + idempotency** (MEDIUM #10):
- 200 if already acknowledged (returns original; still writes
  duplicate-ack audit row)
- 404 if alert ID unknown (no audit-log row)
- 409 if alert auto-resolved before acknowledge (still writes late-ack
  audit row)
- First writer wins; second sees 409
- State change AND audit-log write happen in single SQLite transaction;
  failure rolls back both

**`AlertsConfig` Pydantic model** (NEW): `acknowledgment_required_severities: list[str] = ["critical"]`.

### D9b — WebSocket fan-out + persistence + auto-resolution policy + retention (Session 5a.2)

**WebSocket fan-out:** new endpoint `WS /ws/v1/alerts` fans out alert
state changes (new alert, acknowledgment, auto-resolution) in real-time.

**SQLite persistence + restart recovery:** alert state persists to
`alert_state` table in `data/operations.db`. On restart, HealthMonitor
rehydrates alert state from SQLite BEFORE event bus subscription
becomes active.

**Auto-resolution policy table** (HIGH #1):

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

**Retention** (MEDIUM #9):
- `phantom_short_override_audit` and `alert_acknowledgment_audit`
  tables: retain forever (configurable via
  `audit_log_retention_days: int | None = None`)
- `phantom_short_gated_symbols` table: current-state, no retention
- `alert_state` table: archived alerts pruned after 90 days
  (`archived_alert_retention_days: int = 90`)

**VACUUM strategy:** scheduled VACUUM via `asyncio.to_thread` mirroring
the Sprint 31.8 S2 evaluation.db pattern (close → sync VACUUM → reopen).

**Schema-version table + migration framework** in `data/operations.db`
(NEW; first migration framework in ARGUS).

### D10 — IBKR emitter TODO resolution + E2E integration tests (Session 5b)

Resolve:
- `argus/execution/ibkr_broker.py:453` — IBKR Gateway disconnect/reconnect failure
- `argus/execution/ibkr_broker.py:531` — IBKR API auth/permission failure

**Alpaca emitter TODO** (`argus/data/alpaca_data_service.py:593`)
**EXPLICITLY EXCLUDED** — gets resolved by deletion in Sprint 31.94.

**Behavioral anti-regression assertion** (MEDIUM #13) replaces brittle
line-number-based check:

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

End-to-end integration tests assert: emit → HealthMonitor consume →
REST exposure → WebSocket push → operator acknowledgment → audit-log
persistence → auto-resolution per the policy table.

### D11 — Frontend `useAlerts` hook + Dashboard banner (Session 5c)

`frontend/src/hooks/useAlerts.ts` — TanStack Query / WebSocket hybrid:
- Initial state via `GET /api/v1/alerts/active`
- Real-time updates via `WS /ws/v1/alerts`
- Reconnect resilience: REST fallback → resync on reconnect
- Mirrors existing `useObservatory` and `useArena` hooks

`frontend/src/components/AlertBanner.tsx` — persistent banner at top
of Dashboard for any active critical alert. Severity-coded styling.
Acknowledgment button → REST. Disappears within 1s of ack OR
auto-resolution.

### D12 — Toast notification system + acknowledgment UI flow (Session 5d)

`AlertToast` pops up on any page when new critical alert arrives.
Persists until acknowledged or auto-dismissed. Click-to-acknowledge
opens `AlertAcknowledgmentModal` requiring reason text. Toast queue
handles overflow (stacked, oldest-first dismissed when >5).

### D13 — Observatory alerts panel + cross-page integration (Session 5e)

`Observatory.tsx` gains alerts panel: active + historical, sortable /
filterable. `Layout.tsx` mounts `AlertBanner` + `AlertToast` at layout
level so they're visible across all 10 pages. Banner cross-page
persistence asserted via Vitest integration test.

### D14 — DEF-014 closure documentation

`CLAUDE.md` DEF table marks DEF-014 CLOSED. Architecture doc gains §14
(alert observability). DEC-388 filed in decision-log.

## Performance Considerations

`ocaType=1` ("Cancel with block") atomically blocks fills on OCA siblings
when one member fills, until cancellation propagation completes across
sibling order books. Production IBKR latency for this propagation is
typically 50–200ms (paper-trading documented as looser).

**Phase A spike confirmed** (`scripts/spike_ibkr_oca_late_add.py`,
2026-04-27): IBKR's enforcement is even stricter — once any OCA group
member has filled, all subsequent same-group submissions are rejected
with Error 201 "OCA group is already filled." This cost falls on the
**cancelling siblings**, not the order that fired first.

**ocaType=1 over ocaType=2:** ARGUS's bracket model places T1 and T2 at
distinct full-quantity price targets. ocaType=2's "Reduce with block"
reduce-quantity semantics would mean a T1 partial fill silently reduces
T2's remaining quantity — wrong for ARGUS. Native IBKR `parentId`
linkage handles partial-fill T2-stays-alive orthogonally; ocaType=1
adds atomic cancellation when one OCA member fills FULLY (not partially).

**Reverse-rollback escape hatch (RESTART-REQUIRED, H1):**
`ibkr.bracket_oca_type: 0` disables OCA on bracket children.
Mid-session config flip is NOT supported — produces an inconsistent
cohort of in-flight positions. Operator must restart so all positions
reconstruct under the new config.

## Mass-Balance + IMSR Replay

Categorized variance per H2 disposition:
- `expected_partial_fill` — ARGUS placed N shares, M filled, working order outstanding. No flag.
- `eventual_consistency_lag` — ARGUS-side accounting lags broker-side by ≤2 reconciliation cycles (≤120s). No flag.
- `unaccounted_leak` — Shares in broker SELL stream not attributable to either. **Flag**, regardless of size. Exit non-zero.

The 5-share tolerance framing is dropped entirely. Live-enable gate:
zero `unaccounted_leak` rows across 3+ paper sessions.

**IMSR replay test:** Apr 24 paper-session log confirmed at
`logs/argus_20260424.jsonl`. Replay through BacktestEngine harness
with post-fix code; assert IMSR EOD position is 0 (not −200). No
synthetic-recreation fallback.

**Live-IBKR mechanism check (B1/B4):** The OCA late-add spike script
is committed to the repo as a re-runnable regression check.

## Config Changes

| YAML path | Pydantic model | Field name | Default | Session |
|---|---|---|---|---|
| `ibkr.bracket_oca_type` | `IBKRConfig` | `bracket_oca_type` | `1` | 1a |
| `reconciliation.broker_orphan_alert_enabled` | `ReconciliationConfig` | `broker_orphan_alert_enabled` | `true` | 2b.1 |
| `reconciliation.broker_orphan_entry_gate_enabled` | `ReconciliationConfig` | `broker_orphan_entry_gate_enabled` | `true` | 2c.1 |
| `reconciliation.broker_orphan_consecutive_clear_threshold` | `ReconciliationConfig` | `broker_orphan_consecutive_clear_threshold` | `5` | 2c.2 |
| `reconciliation.phantom_short_aggregate_alert_threshold` | `ReconciliationConfig` | `phantom_short_aggregate_alert_threshold` | `10` | 2d |
| `alerts.acknowledgment_required_severities` | `AlertsConfig` (NEW) | `acknowledgment_required_severities` | `["critical"]` | 5a.1 |
| `alerts.auto_resolve_on_condition_cleared` | `AlertsConfig` | `auto_resolve_on_condition_cleared` | `true` | 5a.2 |
| `alerts.audit_log_retention_days` | `AlertsConfig` | `audit_log_retention_days` | `null` | 5a.2 |
| `alerts.archived_alert_retention_days` | `AlertsConfig` | `archived_alert_retention_days` | `90` | 5a.2 |

## Relevant Decisions

- **DEC-385 reserved** — Side-aware reconciliation contract. Spans
  6 sessions (2a / 2b.1 / 2b.2 / 2c.1 / 2c.2 / 2d).
- **DEC-386 reserved** — OCA-group threading + broker-only safety. Spans
  4 sessions (0 / 1a / 1b / 1c).
- **DEC-388 reserved** — Alert observability architecture. Resolves DEF-014.
  Spans 6 sessions (5a.1 / 5a.2 / 5b / 5c / 5d / 5e).

---

# Embedded: Specification by Contradiction

> Source: `spec-by-contradiction.md` (Phase C-1 third-pass cleared, 2026-04-27).

## Out of Scope

These items are related to DEF-204 fix work but are explicitly excluded from Sprint 31.91:

1. **Modifying DEF-199's A1 fix.** The 3-branch pattern at
   `argus/execution/order_manager.py:1670-1698` (EOD Pass 1 retry) and
   `:1719-1750` (EOD Pass 2). Session 3 mirrors this pattern; it does NOT
   modify the A1 code itself.

2. **Modifying IMPROMPTU-04's startup invariant.**
   `check_startup_position_invariant()` in `argus/main.py` and the
   `ArgusSystem._startup_flatten_disabled` attribute are out of scope.

3. **Adding `Position.broker_side: OrderSide` to the Pydantic Position
   model.** `Position.side: OrderSide` already exists at
   `argus/models/trading.py:160`. Adding `broker_side` would be
   redundant.

4. **Changing `Position.shares` Pydantic constraint.**
   `shares: int = Field(ge=1)` stays.

5. **Touching AlpacaBroker.** Out of scope end-to-end. Exception:
   Session 0 adds `cancel_all_orders(symbol)` ABC compliance impl via
   `DeprecationWarning` per L1; this is the only AlpacaBroker change
   permitted.

6. **`argus/data/alpaca_data_service.py:593` Alpaca emitter TODO** —
   explicitly OUT of scope. Sprint 31.94 retires Alpaca by deletion.
   Behavioral anti-regression test in Session 5b.

7. **DEF-194/195/196 reconnect-recovery.** Lives in Sprint 31.93.

8. **DEF-175/182/201/202 component ownership consolidation.** Lives
   in Sprint 31.92.

9. **Re-enabling live trading.** Downstream gate.

10. **Refactoring `_resubmit_stop_with_retry` retry-cap logic.**
    DEC-372's `stop_cancel_retry_max` and exponential-backoff
    schedule are unchanged. Session 1b only adds `ocaGroup`.

11. **Adding new exit-management semantics.** No new strategies for
    cancelling bracket children, no new exit reasons, no changes to
    trail/escalation activation logic. Only the `Order` objects
    produced by those decisions get OCA-group decoration.

12. **Backporting OCA grouping to existing managed positions.**
    Positions in `_managed_positions` at the time Session 1a deploys
    have `oca_group_id = None`. Operator daily flatten remains the
    safety net.

13. **Modifying SimulatedBroker's existing simulation logic.**
    SimulatedBroker gains a no-op acknowledgment of `ocaGroup` /
    `ocaType` (so unit tests pass without error) but its
    fill-simulation logic is unchanged. No "simulated OCA cancellation"
    behavior is added.

## Edge Cases to Reject

| Edge Case | Expected Behavior |
|-----------|-------------------|
| Bracket parent ULID is empty/None at the time `ocaGroup` is derived | Fall back to generating a fresh ULID via `generate_id()` |
| `ManagedPosition.oca_group_id` is None when `_trail_flatten` is invoked | Place SELL with no `ocaGroup` (legacy behavior); log INFO once |
| Two `ManagedPosition` instances exist for the same symbol simultaneously | Each carries its own distinct `oca_group_id`; both bracket trees operate independently |
| IBKR rejects an order with `ocaType=1` | Log ERROR; let the existing rollback path cancel the parent |
| Reconciliation runs before any positions are tracked (cold-start) | `broker_positions` empty; both branches skip; no alert |
| Broker-orphan position has `side` field missing (older Position payload) | Log ERROR; do not engage entry gate; do not emit `phantom_short` alert (could be a long-orphan with stale type) |
| Broker-orphan position has `side == OrderSide.BUY`, cycles 1–2 | Log WARNING only; no entry gate, no alert |
| Broker-orphan position has `side == OrderSide.BUY`, cycle ≥3 | Emit `stranded_broker_long` alert (severity warning); still no entry gate |
| `_check_flatten_pending_timeouts` queries the broker and the API call raises | Existing `except Exception` path preserved |
| Phantom-short entry-gate is engaged and operator wants to manually unblock | Operator hits override API; audit-log entry. Auto-clear via 5-cycle threshold also available |
| Same symbol gets phantom-short flagged AND has a margin-circuit gate | Both gates remain in effect; symbol is doubly-blocked |

## Scope Boundaries — Do NOT Modify

- `argus/execution/order_manager.py:1670-1698` — DEF-199 A1 fix Pass 1 retry
- `argus/execution/order_manager.py:1707-1750` — DEF-199 A1 fix Pass 2
- `argus/main.py` — startup invariant region (`check_startup_position_invariant()`,
  `_startup_flatten_disabled` flag, the gate around
  `OrderManager.reconstruct_from_broker()`)
- `argus/models/trading.py` — `Position` class (existing `side` field is
  consumed; `shares: int = Field(ge=1)` constraint preserved)
- `argus/execution/alpaca_broker.py` — business logic. Exception: Session 0
  adds `cancel_all_orders(symbol)` ABC-compliance impl via `DeprecationWarning`
- `argus/data/alpaca_data_service.py:593` — Alpaca emitter TODO. Anti-regression
  test in Session 5b verifies the TODO comment is still present.
- `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` (historical artifact)
- `workflow/` submodule (RULE-018)

## Scope Boundaries — Do NOT Refactor

- `_check_flatten_pending_timeouts` general structure (only side-check added)
- `place_bracket_order` general structure (only `ocaGroup` / `ocaType` Order-field
  setting added)
- `reconcile_positions` outer-loop structure (only the broker-orphan branch is new)
- `Position` model field names or types (no fields renamed or restructured)

## Scope Boundaries — Do NOT Add

- New `OrderType` enum values
- A "simulated OCA cancellation" behavior in SimulatedBroker
- A new `ExitReason` enum value for "phantom_short" (existing
  `ExitReason.RECONCILIATION` covers it)
- A new event class (existing `SystemAlertEvent` at
  `argus/core/events.py:405` has all needed fields)
- A new circuit breaker (per-symbol entry gate is a set membership check,
  not a circuit)

## Interaction Boundaries — Behaviors NOT Changed

- DEC-117 atomic bracket invariant: parent fails → all children cancelled.
  Preserved by `ibkr_broker.py:783-805`.
- DEC-369 broker-confirmed positions never auto-closed: `confirmed`
  branch at line 3045 unchanged; new broker-orphan branch fires only
  for UNCONFIRMED.
- DEC-370 auto-cleanup-unconfirmed default false: unchanged.
- DEC-372 stop retry caps: unchanged.
- DEC-367 margin circuit breaker: unchanged. Per-symbol phantom-short
  entry gate is a separate state.
- Sprint 29.5 EOD flatten circuit breaker: unchanged.
- DEF-158 dup-SELL prevention: Session 3 modifies the exact function;
  the dup-SELL prevention semantics for the ARGUS=N, IBKR=N normal case
  are preserved by construction.
- OrderApprovedEvent → OrderManager → Broker pipeline: unchanged. The
  per-symbol entry gate adds a pre-broker rejection.

## Deferred to Future Sprints

| Item | Target Sprint | DEF |
|------|--------------|---------------|
| Component-ownership consolidation for `OrderManager` (DEF-175/182/201/202) | Sprint 31.92 | Pre-existing |
| Reconnect-recovery and RejectionStage enum (DEF-194/195/196) | Sprint 31.93 | Pre-existing |
| AlpacaBroker retirement (DEF-178/183) | Sprint 31.94 | Pre-existing |
| HealthMonitor consumer for the new `phantom_short` alert | This sprint Sessions 5a.1+5a.2 | DEF-014 (CLOSED at sprint close) |
| Backend boot-commit-pair logging automation | Unscheduled | DEF-207 (pre-existing) |
| SimulatedBroker should simulate OCA-group cancellation semantics matching ocaType=1 | Unscheduled | DEF-208 (file at sprint close) |
| `analytics/debrief_export.py` and other historical-record writers must preserve `Position.side` | Sprint 35+ horizon | DEF-209 (file at sprint close) |
| `POST /api/v1/system/suspend` endpoint to allow live-rollback policy automation | Unscheduled | DEF-210 (file at sprint close) |
| Side-aware breakdown in post-flatten verification log line at `order_manager.py:1729` | Unscheduled | DEF-211 (file at sprint close) |

---

# Embedded: Sprint-Level Regression Checklist

> Source: `regression-checklist.md` (Phase C-1 third-pass cleared, 2026-04-27).
> 22 critical invariants. Each Tier 2 review verdict report MUST contain
> this checklist as a table with each item marked PASS / FAIL / N/A.

## Critical Invariants (Must Hold After Every Session)

### 1. DEF-199 A1 fix detects + refuses 100% of phantom shorts at EOD

**Test:** Pre-existing `test_short_position_is_not_flattened_by_pass2`
(in `tests/test_sprint329.py` or sibling).

**Verified at:** Every session. The A1 fix is on the do-not-modify list.
Tier 2 review verifies `git diff` shows no edits to
`order_manager.py:1670-1750`.

**Sessions:** ALL.

### 2. DEF-199 A1 EOD Pass 1 retry still respects side check

**Test:** Pre-existing `test_pass1_retry_skips_short_position`.

**Sessions:** ALL.

### 3. DEF-158 dup-SELL prevention works for the ARGUS=N, IBKR=N normal case

**Test:** Pre-existing `test_def158_flatten_qty_mismatch_uses_broker_qty`.

**Sessions:** Session 3 must explicitly include
`test_def158_retry_long_position_flattens_normally` in its DoD.

### 4. DEC-117 atomic bracket invariant: parent fails → all children cancelled

**Test:** Force the bracket children placement to raise mid-loop; assert
the rollback at `ibkr_broker.py:783-805` fires; assert parent order is
cancelled.

**Sessions:** Session 1a's Tier 2 review explicitly verifies `git diff`
on `ibkr_broker.py:783-805` shows zero edits.

### 5. Existing 5,080 pytest baseline holds; new tests are additive only

**Test:** `pytest --ignore=tests/test_main.py -n auto -q` returns ≥5,080
passing post-session.

**Sessions:** ALL.

### 6. `tests/test_main.py` baseline holds (39 pass + 5 skip)

**Test:** `pytest tests/test_main.py -q` returns 39 pass + 5 skip.

**Sessions:** ALL. Session 2a touches `main.py` and is the most likely
site to affect `test_main.py`; close-out must explicitly cite the count.

### 7. Vitest baseline holds at 866 (rises with frontend sessions)

**Test:** `npm test` (or equivalent) returns ≥866 passing.

**Sessions:** ALL backend (count unchanged); 5c–5e add to it.

### 8. Risk Manager check 0 (`share_count ≤ 0` rejection) unchanged

**Test:** Risk Manager still rejects `share_count <= 0` before any other
check fires.

**Verified at:** Every session via `git diff` audit on
`argus/core/risk_manager.py` (zero edits across the entire sprint EXCEPT
Session 2b.2's two long-only filter additions at `:335` and `:771`).

**Sessions:** ALL.

### 9. IMPROMPTU-04 startup invariant unchanged

**Test:** Pre-existing `test_single_short_fails_invariant`,
`test_all_long_positions_returns_ok`,
`test_position_without_side_attr_fails_closed`.

**Verified at:** `git diff` on `main.py` startup region — zero edits except
Session 2a's reconciliation call site at `:1505-1535` (BELOW the
startup invariant region).

**Sessions:** ALL. Session 2a needs explicit verification.

### 10. DEC-367 margin circuit breaker unchanged

**Test:** Pre-existing margin-circuit tests.

**Sessions:** ALL. Session 2c.1's per-symbol entry gate MIRRORS the
DEC-367 pattern shape but does NOT extend or modify the existing margin
circuit; the two states are independent.

### 11. Sprint 29.5 EOD flatten circuit breaker unchanged

**Test:** Pre-existing EOD-flatten-circuit-breaker tests.

**Sessions:** ALL.

### 12. Pre-existing flakes did not regress

**Test:** Run the full suite 3× via `pytest -n auto --count=3` (if
pytest-repeat installed); verify each of DEF-150, DEF-167, DEF-171,
DEF-190, DEF-192 fails at the same or LOWER frequency than baseline.

**Verified at:** Every session's CI run (RULE-050). Tier 2 reviewer
explicitly cites the CI run URL.

**Sessions:** ALL.

### 13. New config fields parse without warnings

**Test:** Load `config/system.yaml` and `config/system_live.yaml` via
the project's standard config loader; assert no Pydantic warnings about
unrecognized keys; assert all new fields load with expected defaults
when YAML omits them, AND with YAML-specified values when YAML includes
them.

**Sessions:** 1a (`bracket_oca_type`), 2b.1
(`broker_orphan_alert_enabled`), 2c.1
(`broker_orphan_entry_gate_enabled`), 2c.2
(`broker_orphan_consecutive_clear_threshold`), 2d
(`phantom_short_aggregate_alert_threshold`), 5a.1
(`AlertsConfig.acknowledgment_required_severities`), 5a.2 (`auto_resolve_on_condition_cleared`,
`audit_log_retention_days`, `archived_alert_retention_days`).

### 14. Monotonic-safety property holds at each session merge (19-row matrix)

| State | OCA bracket | OCA standalone (4) | Broker-only safety | Restart safety | Recon detects shorts | DEF-158 retry side-aware | Mass-balance validated | Alert observability |
|-------|---|---|---|---|---|---|---|---|
| After Session 0 | NO | NO | NO | NO | NO | NO | NO | NO |
| After Session 1a | YES | NO | NO | NO | NO | NO | NO | NO |
| After Session 1b | YES | YES | NO | NO | NO | NO | NO | NO |
| After Session 1c | YES | YES | YES | YES | NO | NO | NO | NO |
| After Session 2a | YES | YES | YES | YES | NO (typed only) | NO | NO | NO |
| After Session 2b.1 | YES | YES | YES | YES | partial (alert only) | NO | NO | NO |
| After Session 2b.2 | YES | YES | YES | YES | partial + side-aware reads (4 filter + 1 alert-align) | NO | NO | NO |
| After Session 2c.1 | YES | YES | YES | YES | full (alert + gate + persistence) | NO | NO | NO |
| After Session 2c.2 | YES | YES | YES | YES | full + auto-clear (5-cycle) | NO | NO | NO |
| After Session 2d | YES | YES | YES | YES | full + override API + audit + configurable threshold | NO | NO | NO |
| After Session 3 | YES | YES | YES | YES | full | YES | NO | NO |
| After Session 4 | YES | YES | YES | YES | full | YES | YES (script + IMSR replay) | NO |
| After Session 5a.1 | YES | YES | YES | YES | full | YES | YES | partial backend-1 (HealthMonitor consumer + REST + atomic+idempotent ack) |
| After Session 5a.2 | YES | YES | YES | YES | full | YES | YES | full backend (WebSocket + persistence + auto-resolution policy + retention/migration) |
| After Session 5b | YES | YES | YES | YES | full | YES | YES | full backend incl. IBKR emitters + E2E + behavioral Alpaca check |
| After Session 5c | YES | YES | YES | YES | full | YES | YES | partial UI (Dashboard banner only) |
| After Session 5d | YES | YES | YES | YES | full | YES | YES | partial UI (banner + toast + ack modal) |
| After Session 5e | YES | YES | YES | YES | full | YES | YES | full UI (Observatory panel + cross-page) |

Each row strictly safer than the row above. Verified by paper-session
debrief the day after each merge: phantom-short accumulation count must
be ≤ the prior row's count; alert observability features available in
the row's state must not regress.

**Sessions:** ALL — but verification is post-merge, not in-session.

### 15. No items on the do-not-modify list were touched

**Test:** `git diff <session-base>..<session-head>` audit against the
do-not-modify list:

- `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix) — zero edits
- `argus/main.py` startup invariant region — zero edits except:
  - Session 1c's scoped expansion of `reconstruct_from_broker()` body
    to add `cancel_all_orders(symbol)` calls (NOT the call-site gate
    in main.py)
  - Session 2a's scoped reconciliation call-site edit at lines 1505-1535
  - Session 2c.1's startup gate-state rehydration code
  - Session 5a.1's HealthMonitor consumer init
- `argus/models/trading.py` `Position` class (lines 153-173) — zero edits
- `argus/execution/alpaca_broker.py` — zero edits EXCEPT Session 0's
  `cancel_all_orders(symbol)` ABC compliance impl (DeprecationWarning)
- `argus/data/alpaca_data_service.py:593` Alpaca emitter TODO — zero
  edits (verified by anti-regression test in Session 5b)
- `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` — zero edits
- `workflow/` submodule — zero edits

**Sessions:** ALL.

### 16. Bracket placement performance does not regress beyond documented bound

**Test:** Compare bracket-stop fill slippage on a post-Session-1a paper
session vs a pre-Sprint-31.91 baseline. Mean slippage on $7–15 share
universe should not degrade by more than $0.02.

**Sessions:** Session 4 wires this into market-session-debrief.md Phase
7. Earlier sessions are observational only.

### 17. Mass-balance assertion at session debrief (categorized variance)

**Test:** `scripts/validate_session_oca_mass_balance.py
logs/argus_YYYYMMDD.jsonl` exits 0. Per H2 categorized variance:
zero `unaccounted_leak` rows per symbol per session.

**Sessions:** Session 4 delivers; verified at every paper-session
post-merge.

### 18. Alert observability — frontend banner cross-page persistence

**Test:** While a critical alert is active, navigating between Command
Center pages preserves the banner's visibility on every page. Banner
clears within 1s of acknowledgment OR auto-resolution.

**Sessions:** Session 5e delivers via Layout-level mounting.

### 19. Alert observability — WebSocket fan-out reconnect resilience

**Test:** Disconnect WebSocket while a critical alert is active. Frontend:
1. Detect disconnect within 5s
2. Fall back to TanStack Query polling of `GET /api/v1/alerts/active`
3. On reconnect: refetch state via REST and resume WebSocket
4. Recover any alerts emitted during the disconnect window

**Sessions:** Session 5c (frontend resilience); Session 5a.2 (REST
recovery endpoint).

### 20. Alert observability — acknowledgment audit-log persistence

**Test:** After acknowledgment, audit-log entry persists across ARGUS
restart. Querying `alert_acknowledgment_audit` table after restart
returns the entry with full payload.

**Sessions:** Session 5a.1 (table); Session 5a.2 (persistence).

### 21. SimulatedBroker OCA-assertion tautology guard (MEDIUM #11)

**Test:** Grep-based regression test that scans `tests/` for files
that import `SimulatedBroker` AND assert OCA-grouping behavior. Such
tests must use IBKR mocks, not SimulatedBroker, because SimulatedBroker's
OCA implementation is a no-op acknowledgment.

```python
def test_no_oca_assertion_uses_simulated_broker():
    """Anti-tautology guard (MEDIUM #11)."""
    import os, re
    forbidden = []
    for root, _, files in os.walk("tests"):
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            with open(path) as fh:
                src = fh.read()
            uses_sim = "SimulatedBroker" in src
            asserts_oca = bool(re.search(r"oca|OCA|ocaGroup|ocaType", src))
            if uses_sim and asserts_oca:
                if "# allow-oca-sim:" in src:
                    continue
                forbidden.append(path)
    assert not forbidden, (
        f"OCA-behavior tests must use IBKR mocks, not SimulatedBroker. "
        f"Found in: {forbidden}. Mark known-safe cases with "
        f"`# allow-oca-sim: <reason>` comment."
    )
```

**Verified at:** Sprint pre-flight (before Session 0); every backend
session's CI run; sprint-final review.

**Sessions:** Lands in regression-checklist at Session 0 close-out;
enforced thereafter.

### 22. Spike script freshness (HIGH #5)

**Test:** When ARGUS is in paper-trading mode, the most recent
`scripts/spike_ibkr_oca_late_add.py` result file
(`spike-results-YYYY-MM-DD.json`) must be dated within the last 30
days. Failure to return `PATH_1_SAFE` invalidates the OCA-architecture
seal and triggers Tier 3 review.

```python
def test_spike_script_result_dated_within_30_days_in_paper_mode():
    """Spike script freshness guard (HIGH #5)."""
    import os, json, datetime
    spike_dir = "scripts/spike-results"
    if not os.path.isdir(spike_dir):
        return
    files = sorted(
        f for f in os.listdir(spike_dir)
        if f.startswith("spike-results-") and f.endswith(".json")
    )
    if not files:
        return
    latest = files[-1]
    date_str = latest[len("spike-results-"):-len(".json")]
    latest_date = datetime.date.fromisoformat(date_str)  # ISO format
    age_days = (datetime.date.today() - latest_date).days
    assert age_days <= 30
    with open(os.path.join(spike_dir, latest)) as fh:
        result = json.load(fh)
    assert result.get("verdict") == "PATH_1_SAFE"
```

**Sessions:** Lands at Session 4; enforced thereafter.

---

# Embedded: Sprint-Level Escalation Criteria

> Source: `escalation-criteria.md` (Phase C-1 third-pass cleared, 2026-04-27).

## Trigger Conditions (Halt Conditions)

If ANY trigger fires, halt the session, post to the work-journal
conversation, and wait for operator + reviewer disposition.

### A. Mandatory Halts (Tier 3 architectural review automatically fires)

| # | Trigger | Required Response |
|---|---------|-------------------|
| A1 | **Session 1c lands cleanly on `main` and Tier 2 verdict = CLEAR.** | Operator arranges Tier 3 architectural review #1. **Scope: combined diff of Sessions 0 + 1a + 1b + 1c** (per third-pass LOW #17). Tier 3 must verdict CLEAR. Mandatory checkpoint. |
| A1.5 | **Session 5b lands cleanly on `main` and Tier 2 verdict = CLEAR.** | Operator arranges Tier 3 architectural review #2 (alert-observability-backend seal). **Scope: combined diff of Sessions 5a.1 + 5a.2 + 5b**. Mandatory checkpoint. |
| A2 | Any Tier 2 review on any session produces verdict = CONCERNS or ESCALATE. | Halt. Operator + Tier 2 reviewer disposition the finding before next session begins. CONCERNS → typically iterate within the same session. ESCALATE → operator decides whether to revert that session's commit or fix forward. |
| A3 | Paper-session debrief on the day after a session merge shows ANY phantom-short accumulation. | Halt sprint. Revert most recently merged session's commit. Tier 3 architectural review of why the test layer didn't catch the regression. |
| A4 | Session implementation discovers OCA-group ID lifecycle interacts with re-entry in a way the lifecycle tests didn't model. | Halt mid-session. Document in close-out's "Discovered Edge Cases" section. Tier 3 review of whether spec needs revision. |
| A5 | Session 1a's bracket OCA grouping causes ANY change to DEC-117 atomic-bracket end-to-end behavior. | Halt. The do-not-modify boundary on DEC-117 was crossed. Operator decides whether to refine the OCA-grouping approach or accept a DEC-117 amendment. |
| A6 | Session 2c's per-symbol entry gate enters a state from which it cannot self-clear (>5 reconciliation cycles after broker reports zero). | Halt. The deadlock concern materialized despite the 5-cycle clear-threshold defense. Tier 3 review. |
| A7 | Session 4's mass-balance script reports any `unaccounted_leak` row on a clean post-merge paper session. | Halt sprint. Mass-balance is the falsifiable validation; if it fails post-merge, the fix is incomplete. Tier 3 review. |
| A8 | Bracket placement performance regresses beyond the documented 50–200ms fill-latency cost (mean degrades by >$0.05 on $7–15 share universe). | Halt. Tier 3 evaluates whether to roll back to `bracket_oca_type: 0`. **Note:** rollback is RESTART-REQUIRED. |
| A9 | WebSocket fan-out reconnect loses alert state without REST recovery (Session 5a/5c). | Halt. Tier 3 review of the WebSocket reconnect resilience design. Alert observability invariant 19. |
| A10 | Frontend banner fails to persist across page navigation while a critical alert is active (Session 5e). | Halt. Banner cross-page persistence is regression invariant 18. Layout-level mounting is incorrect. |
| A11 | Frontend reviewer template not authored in workflow metarepo before Session 5c begins. | Halt before Session 5c. Operator authors the template before 5c proceeds. |
| A12 | Live-enable gate criterion 3a (pre-live paper stress test) OR 3b (live rollback policy) unmet at the live-trading transition decision point. | Halt live-trading consideration. Both criteria must be met. |
| A13 | Spike script result file dated >30 days old when transitioning to live trading or upgrading `ib_async`/IBKR API/Gateway. | Halt the trigger event. Operator re-runs spike. If returns `PATH_1_SAFE`: proceed. Otherwise: rollback to `bracket_oca_type: 0` (RESTART-REQUIRED) or Tier 3 review. |

### B. Mandatory Halts (Tier 3 not required, but operator + Tier 2 reviewer must disposition)

| # | Trigger | Required Response |
|---|---------|-------------------|
| B1 | Pre-existing flake count increases (DEF-150, DEF-167, DEF-171, DEF-190, DEF-192) OR a NEW intermittent failure appears without a DEF entry (RULE-041). | Halt. File DEF entry with symptom + repro hint + xdist worker context. |
| B2 | Test count goes DOWN. | Halt. RULE-019 violation. Implementer explains in close-out which tests were deleted and why. |
| B3 | Pytest baseline ends below 5,080 at the close-out of any session. | Halt. New tests are additive; existing baseline must hold. |
| B4 | CI fails on the session's final commit and the failure is NOT a documented pre-existing flake. | Halt per RULE-050. Do not proceed to next session until CI green. |
| B5 | DISCOVERY's line-number anchors drift more than 5 lines from the spec values during pre-flight grep-verify. | Halt mid-pre-flight. Re-anchor the session's surgical edits against actual current line numbers. |
| B6 | A do-not-modify-list file appears in the session's `git diff`. | Halt. RULE-004 violation. Revert the unintended change before close-out. |
| B7 | Test runtime degrades >2× from baseline OR a single test's runtime exceeds 60 seconds. | Halt and investigate. Per RULE-037, verify no orphaned background processes are inflating runtime. May be DEF-190 (pyarrow/xdist) recurrence. |

### C. Soft Halts (Continue with extra caution + close-out flag)

| # | Trigger | Required Response |
|---|---------|-------------------|
| C1 | Implementer notices a bug or improvement opportunity OUTSIDE the current session's scope. | Document in close-out under "Deferred Items" (RULE-007). Do NOT fix in this session. |
| C2 | First fix attempt fails and a second approach emerges. | Per RULE-008, allow ONE additional approach attempt without operator approval; if that also fails, halt and request guidance. |
| C3 | Two failed fix attempts on the same bug. | Switch to diagnostic-first mode (RULE-030). Build a minimal repro outside the application code. Close-out marks Context State YELLOW. |
| C4 | Context State trending YELLOW. | Per RULE-027, proactively checkpoint: commit, run scoped tests, produce partial close-out, suggest continuing in a fresh session. |
| C5 | Implementer is uncertain whether a change crosses the do-not-modify boundary. | Pause; consult the SbC do-not-modify list explicitly; if still uncertain, escalate to operator. |
| C6 | Phase A's grep-verified line numbers drift 1–5 lines from spec. | Continue (small drift is RULE-038-acknowledged); document the actual line numbers in close-out for the next session's reference. |
| C7 | A test layer's grep regression guard (Session 1b's "no SELL without OCA") false-positives on a legitimate exempt site. | Add an explicit `# OCA-EXEMPT: <reason>` comment at the exempt site. Do NOT remove the regression guard. |

## Escalation Targets

- **Code-level questions** (does this approach work?): Tier 2 reviewer
  is first-line; operator is second-line.
- **Spec-level questions** (does this still match the Sprint Spec?):
  Operator + sprint-planning conversation are required.
- **Architectural questions** (does this change a DEC?): Tier 3
  reviewer in a separate Claude.ai conversation, with operator
  dispositioning the verdict.
- **Safety questions** (does this risk paper-trading regressions or
  live trading consideration?): Operator + Tier 3 reviewer; pause
  paper trading if in doubt.

## Sprint Abort Conditions

The sprint as a whole is aborted if ANY of:

1. **Two or more A-class halts within the same week.** Indicates the
   spec or the underlying mechanism understanding is wrong.
2. **DEF-204 mechanism turns out to be different from IMPROMPTU-11's
   diagnosis.** A paper session shows phantom shorts even after Session
   1a's bracket OCA fix lands. Investigate per RULE-051
   (mechanism-signature-vs-symptom).
3. **Operator paper-trading mitigation breaks**
   (`scripts/ibkr_close_all_positions.py` fails or is unsafe). Sprint
   pauses until mitigation is restored.
4. **An unrelated upstream sprint changes a key file** (`order_manager.py`,
   `ibkr_broker.py`, `main.py`) in a way that conflicts with this
   sprint's surgical edits. Sprint pauses for rebase + impact assessment.

## Sprint Closure Checks (Final Session)

When Session 5e (the final session) closes out, the close-out report
MUST verify:

- [ ] All 14 Sprint Spec deliverables have all acceptance criteria green.
- [ ] All 22 Sprint-Level Regression Checklist items verified.
- [ ] DEF-204 status update prepared for CLAUDE.md (CLOSED with citation chain).
- [ ] DEF-014 status update prepared for CLAUDE.md (CLOSED with citation chain).
- [ ] DEC-385 + DEC-386 + DEC-388 entries drafted for `decision-log.md`.
- [ ] DEF-208 + DEF-209 + DEF-210 + DEF-211 filed.
- [ ] RSK-DEF-204 transition prepared for `risk-register.md`.
- [ ] `architecture.md` §3.7 + §3.3 + §13 + §14 (NEW) updates drafted.
- [ ] Cross-reference rename updates from artifact 6 (Doc Update Checklist) verified complete.

These checks gate the sprint-close phase, not just Session 5e. The
doc-sync follow-on is a separate session per RULE-014; this sprint's
final session **writes the doc-update files** (with surgical patches)
but the actual file edits land in a follow-on doc-sync session.

---

*End Sprint 31.91 Review Context.*
