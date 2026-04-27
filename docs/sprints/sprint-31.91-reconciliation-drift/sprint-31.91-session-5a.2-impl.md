# Sprint 31.91, Session 5a.2: WebSocket Fan-Out + SQLite Persistence + Auto-Resolution Policy Table + Retention/Migration

> **Track:** Alert Observability Backend (Session 5a.1 → **5a.2** → 5b).
> **Position in track:** Second session. Adds the durable + real-time half on top of 5a.1's REST contract. Backs the alert state with SQLite (closing 5a.1's restart-loses-alerts gap), introduces the per-alert-type auto-resolution policy table per HIGH #1, the retention policy per MEDIUM #9, and ARGUS's first schema migration framework for `data/operations.db`.

## Pre-Flight Checks

1. **Read `.claude/rules/universal.md`.** RULE-038, RULE-050, RULE-019, RULE-007 all apply.

2. Read these files:
   - Session 5a.1 deliverables on `main` (HealthMonitor in-memory state model, `AlertState` dataclass, `AlertsConfig`).
   - `argus/ws/` — existing WebSocket handler patterns (use `arena.py` or `observatory.py` as structural template).
   - `docs/sprints/sprint-31.8/` — Sprint 31.8 S2 evaluation.db VACUUM-via-`asyncio.to_thread` pattern. Replicate this idiom; do NOT invent a new VACUUM strategy.
   - `data/operations.db` current schema. Run `sqlite3 data/operations.db ".schema"` and capture for reference. The Session 5a.1 `alert_acknowledgment_audit` table is already there; this session adds `alert_state` + `schema_version`.
   - `argus/main.py` — locate the HealthMonitor instantiation site (rehydration line goes BEFORE Event Bus subscription — second scoped exception in invariant 15 for this session).
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D9b + AC-D9b (lines ~347-401, 635+).
   - `argus/core/events.py` — locate event types referenced in auto-resolution predicates: `ReconciliationCompletedEvent`, `IBKRReconnectedEvent`, `DatabentoHeartbeatEvent`, `OrderFilledEvent`. Verify all exist; if any are missing, halt B6 (the predicate can't fire on a non-existent event).

3. Run baseline (full suite):

   ```
   python -m pytest tests/ -n auto -q --ignore=tests/test_main.py
   ```

   Expected: green at Session 5a.1's count.

4. Branch: **`main`**. Verify Session 5a.1 deliverables landed:

   ```bash
   grep -n "AlertState\|on_system_alert\|alert_acknowledgment_audit" argus/core/health.py argus/api/routes/alerts.py
   sqlite3 data/operations.db ".tables" | grep -E "alert|phantom"
   ```

## Objective

Five deliverables:

1. **WebSocket fan-out** at `WS /ws/v1/alerts` — pushes alert state changes (new active, acknowledgment, auto-resolution, archive) to connected clients.
2. **SQLite persistence** for `alert_state` — active and archived alerts survive restart.
3. **Rehydration on startup BEFORE Event Bus subscription** — closes the 5a.1 restart-loses-alerts gap. `main.py` ordering is contractual.
4. **Per-alert-type auto-resolution policy table** per HIGH #1 — predicates evaluated on relevant Event Bus events; `phantom_short` shares the 5-cycle threshold with Session 2c.2's gate-clear (single source of truth).
5. **Retention policy + VACUUM** per MEDIUM #9 + **schema migration framework** (NEW; first in ARGUS).

## Requirements

### WebSocket Fan-Out (`argus/ws/alerts.py`)

Mirror `argus/ws/arena.py` structure. Per-connection state includes:

- Subscribe to internal `alert_state_change` event (HealthMonitor publishes whenever active/archived state mutates).
- Push 4 message types: `alert_active` (new), `alert_acknowledged`, `alert_auto_resolved`, `alert_archived`.
- On WebSocket connect: send full active-alert snapshot first (initial-load equivalent of `GET /alerts/active`); subsequent messages are deltas.

```python
@router.websocket("/ws/v1/alerts")
async def alerts_websocket(ws: WebSocket, health_monitor: HealthMonitor):
    await ws.accept()
    try:
        # Initial snapshot
        await ws.send_json({
            "type": "snapshot",
            "alerts": [a.to_dict() for a in health_monitor.get_active_alerts()],
        })
        # Subscribe to subsequent state changes
        async for msg in health_monitor.subscribe_state_changes():
            await ws.send_json(msg)
    except WebSocketDisconnect:
        ...
```

### SQLite `alert_state` Table

```sql
CREATE TABLE IF NOT EXISTS alert_state (
    alert_id TEXT PRIMARY KEY,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    emitted_at_utc TEXT NOT NULL,
    emitted_at_et TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'active' | 'acknowledged' | 'auto_resolved' | 'archived'
    acknowledged_by TEXT,
    acknowledged_at_utc TEXT,
    acknowledgment_reason TEXT,
    auto_resolved_at_utc TEXT,
    archived_at_utc TEXT
);
CREATE INDEX idx_alert_state_status ON alert_state(status);
CREATE INDEX idx_alert_state_emitted_at ON alert_state(emitted_at_utc);
CREATE INDEX idx_alert_state_alert_type ON alert_state(alert_type);
```

HealthMonitor methods:
- `_persist_alert(state)` — INSERT OR REPLACE on every state mutation (fire-and-forget per-mutation; the table is small).
- `_rehydrate_from_db()` — called from `main.py` BEFORE Event Bus subscription.

### Rehydration Ordering (`argus/main.py`)

```python
# Sprint 31.91 Session 5a.2: rehydrate alert state BEFORE subscribing to
# SystemAlertEvent. Without this ordering, alerts emitted between
# rehydration and subscription are lost.
await health_monitor.rehydrate_alerts_from_db()
event_bus.subscribe(SystemAlertEvent, health_monitor.on_system_alert)
```

This is the second scoped exception to invariant 15 for this session (Session 5a.1's subscription line is the existing one; 5a.2 inserts the rehydration call IMMEDIATELY BEFORE it). Document both edits in close-out.

### Auto-Resolution Policy Table (HIGH #1)

Per spec D9b lines 364-373, the policy table:

| Alert type | Auto-resolution condition | Operator ack required? |
|---|---|---|
| `phantom_short` | 5 cycles zero-shares for symbol (matches 2c.2 gate clear-threshold) | No |
| `stranded_broker_long` | broker reports zero for symbol | No |
| `phantom_short_retry_blocked` | NEVER auto-resolves | **Yes** |
| `cancel_propagation_timeout` | NEVER auto-resolves | **Yes** |
| `ibkr_disconnect` | successful subsequent IBKR operation | No |
| `ibkr_auth_failure` | successful subsequent IBKR-authenticated operation | No |
| `databento_dead_feed` | 3 healthy heartbeats | No |
| `phantom_short_startup_engaged` | all engaged symbols cleared OR 24h elapsed | **Yes** |

Implement as a registry of predicate functions:

```python
# argus/core/alert_auto_resolution.py
class AutoResolutionPredicate(Protocol):
    """Returns True when the alert's cleared-condition is met."""
    def __call__(self, alert: AlertState, event: BaseEvent) -> bool: ...

PHANTOM_SHORT_PREDICATE = ...  # consumes ReconciliationCompletedEvent;
                                # checks broker_shares==0 for `5` consecutive
                                # cycles (config: shared with
                                # broker_orphan_consecutive_clear_threshold
                                # from Session 2c.2)

NEVER_AUTO_RESOLVE = lambda alert, event: False  # for phantom_short_retry_blocked + cancel_propagation_timeout

POLICY_TABLE: dict[str, AutoResolutionPredicate] = {
    "phantom_short": PHANTOM_SHORT_PREDICATE,
    "stranded_broker_long": ...,
    "phantom_short_retry_blocked": NEVER_AUTO_RESOLVE,
    "cancel_propagation_timeout": NEVER_AUTO_RESOLVE,
    "ibkr_disconnect": IBKR_RECONNECT_PREDICATE,
    "ibkr_auth_failure": IBKR_AUTH_SUCCESS_PREDICATE,
    "databento_dead_feed": DATABENTO_HEARTBEAT_PREDICATE,
    "phantom_short_startup_engaged": ...,  # 24h elapsed OR all symbols cleared
}
```

**Critical: `phantom_short`'s 5-cycle threshold MUST share the config field with Session 2c.2's gate-clear.** Read `broker_orphan_consecutive_clear_threshold` from `ReconciliationConfig`. Do NOT define a duplicate field; that would let auto-resolution and gate-clear drift apart and produce confusing operator behavior.

HealthMonitor wires the policy table:

```python
# Subscribe to all events that auto-resolution predicates depend on.
event_bus.subscribe(ReconciliationCompletedEvent, self._evaluate_predicates)
event_bus.subscribe(IBKRReconnectedEvent, self._evaluate_predicates)
event_bus.subscribe(DatabentoHeartbeatEvent, self._evaluate_predicates)
event_bus.subscribe(OrderFilledEvent, self._evaluate_predicates)  # for ibkr_auth_failure clearance

async def _evaluate_predicates(self, event):
    for alert_id, alert in list(self._active_alerts.items()):
        predicate = POLICY_TABLE.get(alert.alert_type)
        if predicate is None:
            continue
        if predicate(alert, event):
            await self._auto_resolve(alert_id, event)
```

`_auto_resolve` mutates state to `auto_resolved`, persists, publishes WebSocket message, writes audit row with `acknowledgment_outcome="auto_resolution"` (extends 5a.1's audit semantics; this is a NEW outcome value — verify the table schema's CHECK constraint, if any, allows it; if the schema is open-typed TEXT, no migration needed).

### Retention Policy (MEDIUM #9)

Add to `AlertsConfig`:

```python
auto_resolve_on_condition_cleared: bool = True
audit_log_retention_days: int | None = Field(
    default=None,
    description="None = forever. Forensic data retained by default.",
)
archived_alert_retention_days: int = Field(default=90, ge=1, le=3650)
```

Background retention task (asyncio task):
- Daily: DELETE from `alert_state` WHERE `status='archived'` AND `archived_at_utc < now - archived_alert_retention_days days`.
- Daily: DELETE from `alert_acknowledgment_audit` WHERE `timestamp_utc < now - audit_log_retention_days days` (only if `audit_log_retention_days` is not None; default None = retain forever).
- Post-DELETE: `VACUUM` via Sprint 31.8 S2 idiom: close aiosqlite connection → `await asyncio.to_thread(sync_vacuum, db_path)` → reopen.

### Schema Migration Framework (MEDIUM #9)

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    schema_name TEXT PRIMARY KEY,  -- e.g. 'operations'
    version INTEGER NOT NULL,
    applied_at_utc TEXT NOT NULL,
    description TEXT NOT NULL
);
```

Migration registry pattern (`argus/data/migrations/operations.py`):

```python
MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description="Sprint 31.91 Session 5a.1+5a.2: alert_state + alert_acknowledgment_audit + phantom_short_gated_symbols + phantom_short_override_audit",
        up=...,  # callable that issues the CREATE TABLE statements
        down=...,  # callable that DROPs them; for rollback (advisory; ARGUS doesn't auto-rollback in production)
    ),
]

async def apply_migrations(db_path):
    """Run on startup. Reads schema_version; applies migrations
    forward one at a time; records each in schema_version."""
    ...
```

The first migration encompasses all tables created in 5a.1 + 5a.2 (or split into two migrations — operator preference). The framework's job is to make future schema changes pluggable without ad-hoc CREATE TABLE in random places.

## Tests (~7-12 new pytest)

1. `test_ws_alerts_pushes_state_changes_realtime` — connect WS client; emit alert; assert client received `alert_active` message with full state.
2. `test_ws_alerts_pushes_acknowledgment_state_change` — connect WS; emit; ack via REST; assert client received `alert_acknowledged`.
3. `test_alert_state_persists_to_sqlite_for_restart_recovery` — emit alert; query `alert_state` table directly; assert row present with `status='active'`.
4. `test_alert_state_rehydrated_before_event_bus_subscription` — populate `alert_state` table directly (simulating prior session); construct fresh HealthMonitor + main.py harness; assert rehydration ran BEFORE subscription (use a sentinel: emit a `SystemAlertEvent` BETWEEN constructor and subscription wiring; assert it's IN `_active_alerts` because rehydration completed before the subscription window opened).
5. `test_auto_resolution_policy_phantom_short_5_cycles_zero_shares` — emit phantom_short alert for AAPL; emit 5 `ReconciliationCompletedEvent`s where AAPL has zero shares; assert alert auto_resolved on 5th cycle (matches 2c.2 gate-clear).
6. `test_auto_resolution_policy_phantom_short_retry_blocked_never_auto` — emit phantom_short_retry_blocked alert; emit 100 reconciliation completions; assert alert STILL active (never auto-resolves).
7. `test_auto_resolution_policy_cancel_propagation_timeout_never_auto` — same shape; never auto-resolves.
8. `test_auto_resolution_policy_databento_dead_feed_3_healthy_heartbeats` — emit dead_feed alert; emit 3 `DatabentoHeartbeatEvent`s; assert auto_resolved on 3rd.
9. `test_audit_log_retention_forever_default` — populate audit-log rows with old timestamps; run retention task; assert nothing deleted (default None = forever).
10. `test_archived_alert_retention_90_days_default_purges_older` — populate `alert_state` with `status='archived', archived_at_utc=100 days ago`; run retention; assert deleted.
11. `test_operations_db_schema_version_table_records_initial_migration` — fresh DB; apply migrations; assert `schema_version` has row with `version=1`.
12. `test_vacuum_scheduled_via_asyncio_to_thread_pattern` — instrument the VACUUM call; assert it goes through `asyncio.to_thread`, not direct execution on the event loop.
13. `test_phantom_short_auto_resolution_uses_2c2_threshold_field` — verify the predicate reads `broker_orphan_consecutive_clear_threshold`, not a separate config field. Override threshold to 3; emit alert; emit 3 zero-shares cycles; assert auto_resolved on 3rd.

## Definition of Done

- [ ] `WS /ws/v1/alerts` functional; 4 message types; initial snapshot on connect.
- [ ] `alert_state` SQLite table with full schema + 3 indexes.
- [ ] Rehydration in `main.py` BEFORE Event Bus subscription (line ordering verified by test 4).
- [ ] Auto-resolution policy table covers all 8 alert types with predicates.
- [ ] `phantom_short` predicate shares `broker_orphan_consecutive_clear_threshold` with Session 2c.2 (single config source).
- [ ] Retention policy + daily background task + VACUUM via `asyncio.to_thread`.
- [ ] Schema migration framework + `schema_version` table + first migration registered.
- [ ] 7-12 new pytest tests; all green.
- [ ] CI green; pytest baseline ≥ Session 5a.1 + 7-12.
- [ ] Tier 2 review (backend safety reviewer) verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-5a.2-closeout.md`.

## Close-Out Report

Standard structure plus:

- **Persistence boundary closed:** explicit note that 5a.1's in-memory-only restriction is now lifted; restart-survives is verified by tests 3 + 4.
- **Auto-resolution single-source-of-truth:** cite the line in the predicate where `broker_orphan_consecutive_clear_threshold` is read from `ReconciliationConfig`, not from a duplicate field.
- **Migration framework:** document the pattern in close-out for future-sprint reference. Future schema changes register a `Migration` object and don't touch `CREATE TABLE` directly.
- **Test scaffolding cleanup:** remove the `auto_resolved` status injection scaffolding noted in 5a.1's close-out (replaced by real auto-resolution predicates).

```json
{
  "session": "5a.2",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 12,
  "auto_resolution_policy_complete": true,
  "schema_migration_framework_introduced": true,
  "phantom_short_threshold_single_source": true
}
```

## Tier 2 Review Invocation

Standard pattern. Backend safety reviewer template.

Reviewer output: `docs/sprints/sprint-31.91-reconciliation-drift/session-5a.2-review.md`.

## Session-Specific Review Focus

1. **Rehydration ordering.** Read `main.py` diff. The rehydration call MUST be on the line immediately preceding the `event_bus.subscribe(SystemAlertEvent, ...)` line. If a non-trivial expression sits between them (anything that could `await` and yield to a task that publishes a `SystemAlertEvent`), the test 4 sentinel can fail under load even if it passes in isolation. Reviewer reads the surrounding 10 lines.

2. **`phantom_short` predicate uses 2c.2's threshold.** Test 13 is the structural pin. Reviewer also reads the predicate's source for `self._config.reconciliation.broker_orphan_consecutive_clear_threshold` — NOT a new field, NOT a hardcoded 5.

3. **NEVER_AUTO_RESOLVE is actually `lambda: False`, not omission.** Per HIGH #1, `phantom_short_retry_blocked` and `cancel_propagation_timeout` MUST be in the policy table with explicit never-resolve predicates. Omitting them from the table would have the same runtime effect (no predicate → no resolution) but loses the architectural property that the table is exhaustive. Reviewer verifies all 8 alert types are present in `POLICY_TABLE`.

4. **Migration framework rollback.** The `down` callable in `Migration` is advisory — production doesn't auto-rollback. Reviewer verifies this is documented in code comments AND in the close-out.

5. **VACUUM doesn't block event loop.** Test 12 is the structural pin. Sprint 31.8 S2's pattern is `close → asyncio.to_thread(sync_vacuum) → reopen`. Reviewer verifies the implementation matches.

6. **Retention task scheduling.** Daily — verify the task uses `asyncio.create_task` with appropriate sleep, NOT `time.sleep` (would block). Pattern should match other long-running ARGUS background tasks.

7. **Audit-log row for auto_resolution.** When predicate fires, write a row to `alert_acknowledgment_audit` with `acknowledgment_outcome="auto_resolution"` and `operator_id="auto"`. Per spec D9a line 342. Reviewer verifies this row appears.

## Sprint-Level Regression Checklist

- **Invariant 1:** PASS.
- **Invariant 5:** PASS — expected ≥ Session 5a.1 + 12.
- **Invariant 14:** Row "After Session 5a.2" — Alert observability = "REST + WS + persistence + auto-resolution + retention".
- **Invariant 15:** PASS with scoped exception (5a.2 main.py rehydration line, immediately before 5a.1's subscription).

## Sprint-Level Escalation Criteria

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **A4** (rehydration interacts with Event Bus startup ordering in a way test 4 doesn't model — most likely failure mode for this session).
- **B1, B3, B4, B6** — standard.
- **C5** (main.py edit scope).
- **C7** (existing event-bus tests fail because the new `_evaluate_predicates` subscriber pulls events that previous tests didn't expect to be consumed).

---

*End Sprint 31.91 Session 5a.2 implementation prompt.*
