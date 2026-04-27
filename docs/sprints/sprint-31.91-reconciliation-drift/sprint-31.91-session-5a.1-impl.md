# Sprint 31.91, Session 5a.1: HealthMonitor Consumer + REST Endpoints + Acknowledgment (Atomic + Idempotent)

> **Track:** Alert Observability (Sessions 5a.1 → 5a.2 → 5b → 5c → 5d → 5e). Resolves DEF-014.
> **Position in track:** First session. Backend half-1 of alert observability per HIGH #1 split. Gates Tier 3 architectural review #2 after Session 5b lands.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full.** RULE-038, RULE-050, RULE-019, RULE-007.

2. Read these files to load context:
   - `argus/core/health.py` — current `HealthMonitor` class (Session 5a.1 expands its consumer responsibilities)
   - `argus/core/events.py:405` — `SystemAlertEvent` schema (HealthMonitor subscribes to this)
   - `argus/api/routes/` — existing route file patterns; identify the conventions for new routers (`grep -rn "APIRouter\|@router" argus/api/ | head -10`)
   - `argus/main.py` — HealthMonitor instantiation site (the consumer-init scoped exception per invariant 15)
   - All `SystemAlertEvent` emitter sites (subscription targets):
     - `argus/data/databento_data_service.py` (pre-existing emitter)
     - `argus/execution/order_manager.py` — Sessions 2b.1, 2b.2, 2c.1, 2d, 3 emitters
     - `argus/core/health.py` — Session 2b.2 Health integrity check emitter
     - `argus/main.py` — Session 2d startup gated-symbols emitter
     - `argus/execution/ibkr_broker.py:453, :531` — Session 5b will resolve TODOs (not yet emitting in 5a.1; 5a.1 prepares the consumer infrastructure)
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` D9a — Session 5a.1 acceptance criteria

3. Run scoped tests:

   ```
   python -m pytest tests/core/ tests/api/ -n auto -q
   ```

4. Verify branch: **`main`**.

5. Verify ALL prior sessions (0-4) deliverables on `main`:

   ```bash
   grep -n "ReconciliationPosition\|_phantom_short_gated_symbols\|_check_flatten_pending_timeouts" argus/execution/order_manager.py | head -5
   grep -n "phantom_short_override_audit\|phantom_short_gated_symbols" argus/execution/order_manager.py argus/main.py
   ls scripts/validate_session_oca_mass_balance.py
   ls tests/integration/test_imsr_replay.py
   ```

   All must succeed. If not, halt — Session 5a.1 cannot ship without prior reconciliation work.

6. **Pre-flight grep — locate the HealthMonitor instantiation in `main.py`:**

   ```bash
   grep -n "HealthMonitor\|health_monitor" argus/main.py | head -10
   grep -n "subscribe\|register" argus/main.py | head -20
   ```

   The consumer init is the scoped exception in invariant 15. Identify the exact line where HealthMonitor is constructed; the SystemAlertEvent subscription line goes immediately after.

## Objective

Expand `HealthMonitor` to subscribe to `SystemAlertEvent` from the Event Bus and maintain an in-memory active-alert state machine: `active → acknowledged → (auto-resolved on condition-cleared) → archived`. Expose REST endpoints (`GET /api/v1/alerts/active`, `GET /api/v1/alerts/history`, `POST /api/v1/alerts/{alert_id}/acknowledge`).

The acknowledgment flow has two safety-critical properties per third-pass MEDIUM #10:
- **Atomic transitions:** alert state change AND audit-log write happen in a single SQLite transaction; rollback on failure.
- **Idempotency:** 200 / 404 / 409 paths all defined and tested; 200 (already-acknowledged) and 409 (auto-resolved before ack) paths still write audit-log rows.

Session 5a.1 does NOT yet implement WebSocket fan-out or SQLite-persisted alert state — those land in Session 5a.2. Session 5a.1's state is in-memory only; restart loses state. This is the explicit half-1/half-2 split per HIGH #1.

## Requirements

1. **Create `AlertsConfig` Pydantic model** in `argus/core/config.py`:

   ```python
   class AlertsConfig(BaseModel):
       """Sprint 31.91 D9a: alert observability configuration."""

       acknowledgment_required_severities: list[str] = Field(
           default=["critical"],
           description=(
               "Alert severities for which acknowledgment is required (alert "
               "remains visible until operator acks). 'critical' alerts MUST "
               "be acknowledged. 'warning' and 'info' auto-archive on "
               "auto-resolution per the 5a.2 policy table."
           ),
       )

       # Note: auto_resolve_on_condition_cleared, audit_log_retention_days,
       # archived_alert_retention_days fields are added in Session 5a.2.
   ```

   Add `AlertsConfig` to the parent `Config` (or `SystemConfig`) model alongside other sub-configs:

   ```python
   class Config(BaseModel):
       # ... existing fields ...
       alerts: AlertsConfig = Field(default_factory=AlertsConfig)
   ```

   Update YAMLs (`config/system_live.yaml`, `config/system_paper.yaml`, `config/system_dev.yaml`) with explicit:

   ```yaml
   alerts:
     acknowledgment_required_severities: ["critical"]
   ```

2. **Expand `HealthMonitor` in `argus/core/health.py` to subscribe to `SystemAlertEvent`:**

   Add a new attribute `_active_alerts: dict[str, ActiveAlert]` (where `ActiveAlert` is a dataclass capturing the alert + lifecycle state) and a `_alert_history: list[ActiveAlert]` (append-only history within the in-memory window):

   ```python
   from dataclasses import dataclass, field
   from datetime import datetime
   from enum import Enum

   class AlertLifecycleState(Enum):
       ACTIVE = "active"
       ACKNOWLEDGED = "acknowledged"
       ARCHIVED = "archived"  # auto-resolved or manually closed

   @dataclass
   class ActiveAlert:
       """Sprint 31.91 D9a: alert lifecycle tracking. In-memory only in
       Session 5a.1; SQLite-backed in Session 5a.2."""
       alert_id: str  # generated UUID4 at consume time
       alert_type: str
       severity: str
       source: str
       message: str
       metadata: dict
       state: AlertLifecycleState = AlertLifecycleState.ACTIVE
       created_at_utc: datetime = field(default_factory=datetime.utcnow)
       acknowledged_at_utc: datetime | None = None
       acknowledged_by: str | None = None  # operator_id from ack request
       archived_at_utc: datetime | None = None
       acknowledgment_reason: str | None = None
   ```

   Subscription handler:

   ```python
   class HealthMonitor:
       def __init__(self, ...):
           # ... existing init ...
           self._active_alerts: dict[str, ActiveAlert] = {}
           self._alert_history: list[ActiveAlert] = []  # last N for /history endpoint
           self._alert_history_max_size = 1000  # in-memory cap; 5a.2 adds SQLite

       async def on_system_alert_event(self, event: SystemAlertEvent) -> None:
           """Sprint 31.91 D9a: HealthMonitor consumer. Maintains active-
           alert state in-memory."""
           import uuid
           alert_id = str(uuid.uuid4())
           alert = ActiveAlert(
               alert_id=alert_id,
               alert_type=event.alert_type,
               severity=event.severity,
               source=event.source,
               message=event.message,
               metadata=event.metadata or {},
           )
           self._active_alerts[alert_id] = alert
           self._alert_history.append(alert)
           # Cap history (5a.2 replaces with SQLite-backed pruning)
           if len(self._alert_history) > self._alert_history_max_size:
               self._alert_history = self._alert_history[-self._alert_history_max_size:]
           self._logger.info(
               "HealthMonitor consumed alert %s (type=%s severity=%s).",
               alert_id, event.alert_type, event.severity,
           )
   ```

   Notes:
   - Session 5a.1 generates alert IDs at consume time. Session 5a.2 may need to align with persisted IDs from prior sessions; for now, in-memory UUID4 suffices.
   - The history cap (1000) is in-memory only; 5a.2 replaces with SQLite-backed pruning + retention policy.

3. **Subscribe HealthMonitor to `SystemAlertEvent` in `main.py` (scoped exception per invariant 15):**

   ```python
   # Sprint 31.91 Session 5a.1: HealthMonitor SystemAlertEvent consumer
   # subscription. Scoped exception per invariant 15 ("Session 5a.1
   # HealthMonitor consumer init"). Subscribe AFTER HealthMonitor
   # construction; BEFORE (or alongside) Event Bus start.
   event_bus.subscribe(SystemAlertEvent, health_monitor.on_system_alert_event)
   ```

   Verify the subscription line is co-located with other `event_bus.subscribe(...)` calls; per RULE-007, do not introduce a new subscription pattern.

4. **Create `argus/api/routes/alerts.py` (NEW file) with the three REST endpoints:**

   ```python
   """Sprint 31.91 D9a: alerts REST endpoints."""

   from typing import Annotated
   from fastapi import APIRouter, Depends, HTTPException
   from pydantic import BaseModel, Field
   from datetime import datetime
   import aiosqlite
   import json

   router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


   class AlertResponse(BaseModel):
       alert_id: str
       alert_type: str
       severity: str
       source: str
       message: str
       metadata: dict
       state: str
       created_at_utc: str
       acknowledged_at_utc: str | None
       acknowledged_by: str | None
       archived_at_utc: str | None
       acknowledgment_reason: str | None


   class AcknowledgeRequest(BaseModel):
       reason: str = Field(min_length=10)
       operator_id: str = Field(min_length=1)


   class AcknowledgeResponse(BaseModel):
       alert_id: str
       acknowledged_at_utc: str
       acknowledged_by: str
       reason: str
       audit_id: int
       state: str  # "acknowledged" or "archived" (if 409 case)


   @router.get("/active", response_model=list[AlertResponse])
   async def get_active_alerts(
       health_monitor: Annotated[HealthMonitor, Depends(get_health_monitor)],
   ) -> list[AlertResponse]:
       """Return all alerts currently in ACTIVE or ACKNOWLEDGED state."""
       results = []
       for alert in health_monitor._active_alerts.values():
           if alert.state in (AlertLifecycleState.ACTIVE, AlertLifecycleState.ACKNOWLEDGED):
               results.append(_alert_to_response(alert))
       return results


   @router.get("/history", response_model=list[AlertResponse])
   async def get_alert_history(
       since: str | None = None,  # ISO timestamp
       health_monitor: Annotated[HealthMonitor, Depends(get_health_monitor)],
   ) -> list[AlertResponse]:
       """Return historical alerts within an optional `since` window."""
       since_dt = datetime.fromisoformat(since) if since else None
       results = []
       for alert in health_monitor._alert_history:
           if since_dt and alert.created_at_utc < since_dt:
               continue
           results.append(_alert_to_response(alert))
       return results


   @router.post("/{alert_id}/acknowledge", response_model=AcknowledgeResponse)
   async def acknowledge_alert(
       alert_id: str,
       payload: AcknowledgeRequest,
       health_monitor: Annotated[HealthMonitor, Depends(get_health_monitor)],
       operations_db_path: Annotated[str, Depends(get_operations_db_path)],
   ) -> AcknowledgeResponse:
       """Atomic + idempotent acknowledgment. Per MEDIUM #10:

       - 200: already-acknowledged (returns original ack info; STILL writes
         duplicate-ack audit row).
       - 200: success path.
       - 404: alert ID unknown; NO audit row written.
       - 409: alert auto-resolved before ack (still writes late-ack audit row).
       """
       if alert_id not in health_monitor._active_alerts:
           # Could be unknown OR already archived
           # Search history for archived state
           archived = next(
               (a for a in health_monitor._alert_history
                if a.alert_id == alert_id and a.state == AlertLifecycleState.ARCHIVED),
               None,
           )
           if archived is None:
               raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
           # 409 — alert auto-resolved before ack; STILL write late-ack audit row
           audit_id = await _write_late_ack_audit(
               operations_db_path, alert_id, payload, archived,
           )
           return AcknowledgeResponse(
               alert_id=alert_id,
               acknowledged_at_utc=datetime.utcnow().isoformat(),
               acknowledged_by=payload.operator_id,
               reason=payload.reason,
               audit_id=audit_id,
               state="archived",
           )

       alert = health_monitor._active_alerts[alert_id]

       # Idempotent 200 path: already acknowledged
       if alert.state == AlertLifecycleState.ACKNOWLEDGED:
           # Write duplicate-ack audit row (operator double-clicked, etc.)
           audit_id = await _write_duplicate_ack_audit(
               operations_db_path, alert, payload,
           )
           return AcknowledgeResponse(
               alert_id=alert_id,
               acknowledged_at_utc=alert.acknowledged_at_utc.isoformat(),
               acknowledged_by=alert.acknowledged_by,
               reason=alert.acknowledgment_reason,
               audit_id=audit_id,
               state="acknowledged",
           )

       # Atomic transition: state change AND audit-log write in one SQLite txn
       now = datetime.utcnow()
       audit_id = await _atomic_acknowledge_transition(
           operations_db_path,
           alert_id,
           payload,
           now,
           lambda: _apply_ack_to_in_memory(alert, payload, now),
       )

       return AcknowledgeResponse(
           alert_id=alert_id,
           acknowledged_at_utc=now.isoformat(),
           acknowledged_by=payload.operator_id,
           reason=payload.reason,
           audit_id=audit_id,
           state="acknowledged",
       )


   async def _atomic_acknowledge_transition(
       db_path, alert_id, payload, now, apply_in_memory_callback,
   ) -> int:
       """Atomic SQLite transaction: insert audit row, then apply in-memory
       state change. Rollback on failure of either step."""
       async with aiosqlite.connect(db_path) as db:
           cursor = await db.execute(
               """
               INSERT INTO alert_acknowledgment_audit
               (timestamp_utc, alert_id, operator_id, reason, audit_kind)
               VALUES (?, ?, ?, ?, ?)
               """,
               (now.isoformat(), alert_id, payload.operator_id, payload.reason, "ack"),
           )
           audit_id = cursor.lastrowid
           # Apply in-memory state change inside the transaction window —
           # if the callback throws, the audit row write is rolled back
           apply_in_memory_callback()
           await db.commit()
       return audit_id
   ```

   The `alert_acknowledgment_audit` table schema:

   ```sql
   CREATE TABLE IF NOT EXISTS alert_acknowledgment_audit (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       timestamp_utc TEXT NOT NULL,
       alert_id TEXT NOT NULL,
       operator_id TEXT NOT NULL,
       reason TEXT NOT NULL,
       audit_kind TEXT NOT NULL  -- "ack", "duplicate_ack", "late_ack", "auto_resolution"
   );

   CREATE INDEX IF NOT EXISTS idx_aaa_alert_id ON alert_acknowledgment_audit(alert_id);
   CREATE INDEX IF NOT EXISTS idx_aaa_timestamp ON alert_acknowledgment_audit(timestamp_utc);
   ```

   Notes:
   - The `audit_kind` enum captures all four audit-row types: `ack` (normal), `duplicate_ack` (already-acked), `late_ack` (auto-resolved before ack), `auto_resolution` (auto-resolution from 5a.2's policy table).
   - The atomic transition pattern uses an in-memory callback inside the SQLite transaction; if either fails, both roll back. This is the MEDIUM #10 acceptance criterion.

5. **Register the new router** in `argus/api/__init__.py` (or wherever routers are wired):

   ```python
   from argus.api.routes.alerts import router as alerts_router
   app.include_router(alerts_router)
   ```

6. **Race resolution behavior:** the first writer wins. If two operators acknowledge simultaneously, the second's transaction either:
   - Sees the alert already in ACKNOWLEDGED state (the duplicate-ack 200 path).
   - Or, if the first happened to acknowledge between the second's "is alert in active state?" check and its transaction begin, the second sees `archived` (the 409 path).

   The atomic transition pattern is what makes this race-safe — without atomicity, both could write audit rows AND apply in-memory mutations, producing two acknowledgers for one alert.

7. **No edits to do-not-modify regions.** Specifically:
   - `argus/execution/order_manager.py:1670-1750`
   - `argus/main.py` startup invariant region — Session 5a.1 has SCOPED exception for the HealthMonitor consumer init line per invariant 15
   - `argus/models/trading.py`, `argus/execution/alpaca_broker.py`, `argus/data/alpaca_data_service.py`, `argus/execution/ibkr_broker.py`, `argus/execution/broker.py`
   - `argus/core/risk_manager.py`
   - `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`, `workflow/`

## Tests (~7 new pytest + 1 mock update)

1. **`test_health_monitor_subscribes_to_system_alert_event`**
   - Construct HealthMonitor + Event Bus.
   - Verify HealthMonitor's `on_system_alert_event` is registered as a subscriber for `SystemAlertEvent`.

2. **`test_health_monitor_maintains_active_alert_state_in_memory`**
   - Publish a `SystemAlertEvent` via Event Bus.
   - Assert: HealthMonitor's `_active_alerts` contains exactly 1 entry with the alert's payload.
   - Assert: `_alert_history` also contains the entry (append-only).

3. **`test_get_alerts_active_returns_current_state`**
   - Setup HealthMonitor with 2 active + 1 acknowledged alerts.
   - GET `/api/v1/alerts/active`.
   - Assert: response contains 3 entries (2 active + 1 acknowledged); no archived entries.

4. **`test_get_alerts_history_returns_within_window`**
   - Setup HealthMonitor with 5 alerts spanning a date range.
   - GET `/api/v1/alerts/history?since=<midpoint>`.
   - Assert: response contains only the 3 alerts after the midpoint.

5. **`test_post_alert_acknowledge_atomic_transition_writes_audit`**
   - Setup: 1 active alert.
   - POST `/api/v1/alerts/{id}/acknowledge` with valid payload.
   - Assert: response 200 with `audit_id` populated; alert state = ACKNOWLEDGED in HealthMonitor; `alert_acknowledgment_audit` table has 1 row with `audit_kind="ack"`.
   - **Atomicity test:** simulate SQLite write failure mid-transaction (mock `aiosqlite.commit` to raise); assert in-memory state unchanged (alert still ACTIVE) AND no audit row persisted.

6. **`test_post_alert_acknowledge_idempotent_200_for_already_acknowledged`**
   - Setup: 1 already-acknowledged alert.
   - POST acknowledge with a NEW operator_id and reason.
   - Assert: response 200 with the ORIGINAL acknowledger info in the response body; new `audit_kind="duplicate_ack"` row written.
   - The original acknowledger info is preserved; the new ack is logged but not promoted.

7. **`test_post_alert_acknowledge_404_for_unknown_id`**
   - POST acknowledge for an alert ID that doesn't exist (never created).
   - Assert: response 404; NO audit-log row written.

8. **`test_post_alert_acknowledge_409_for_auto_resolved_writes_late_ack_audit`** (race resolution)
   - Setup: 1 alert that has been moved to ARCHIVED (via simulated auto-resolution; in 5a.1 this can be done via direct state mutation since 5a.2 hasn't shipped yet).
   - POST acknowledge for that alert ID.
   - Assert: response 200 (or specific status — verify against spec); state="archived" in response; `audit_kind="late_ack"` row written.

   Note: the spec says 200/404/409 paths; 409 is the "alert auto-resolved before ack" scenario. The exact HTTP status (409 vs 200 with state="archived") may vary based on FastAPI conventions; document the choice in close-out.

## Definition of Done

- [ ] `AlertsConfig` Pydantic model with `acknowledgment_required_severities: ["critical"]` default.
- [ ] HealthMonitor consumes `SystemAlertEvent` via Event Bus subscription.
- [ ] HealthMonitor maintains `_active_alerts` (dict) + `_alert_history` (list) in-memory.
- [ ] REST `GET /alerts/active` + `/history` functional.
- [ ] REST `POST /alerts/{id}/acknowledge` writes audit-log entry.
- [ ] Atomic transition (state change AND audit-log write in single SQLite transaction).
- [ ] Idempotency: 200 / 404 / 409 paths all tested; 200 (already-ack) and 409 (late-ack) paths still write audit-log rows.
- [ ] Race resolution: first writer wins; second sees 409.
- [ ] `alert_acknowledgment_audit` SQLite table created in `data/operations.db`.
- [ ] 7 new tests + 1 mock update; all passing.
- [ ] CI green; pytest baseline ≥ 5,166 (5,159 entry + 7 new tests).
- [ ] All do-not-modify list items show zero `git diff` (with scoped exception for `main.py` HealthMonitor consumer init).
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-5a.1-closeout.md`.

## Close-Out Report

Standard structure. Verdict JSON:

```json
{
  "session": "5a.1",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 7,
  "tests_total_after": <fill>,
  "files_created": [
    "argus/api/routes/alerts.py"
  ],
  "files_modified": [
    "argus/core/health.py",
    "argus/core/config.py",
    "argus/main.py",
    "config/system_live.yaml",
    "config/system_paper.yaml",
    "<test files>"
  ],
  "donotmodify_violations": 0,
  "main_py_scoped_exception": "HealthMonitor consumer init",
  "tier_3_track": "alert-observability"
}
```

Cite in close-out:
- Whether the 409 case uses HTTP 409 explicitly or 200-with-state="archived" (FastAPI convention choice).
- The exact `main.py` line of the SystemAlertEvent subscription.
- Confirmation that no SystemAlertEvent emitter sites are modified in 5a.1 (subscription only; emitters at 2b.1, 2b.2, 2c.1, 2d, 3 are unchanged).

## Tier 2 Review Invocation

Standard pattern. Backend safety reviewer template. Review report at `session-5a.1-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Atomic transition correctness.** Read the `_atomic_acknowledge_transition` helper. The SQLite INSERT and the in-memory mutation must both happen inside the connection's transaction window. If the in-memory mutation throws, the SQLite write must roll back (no commit). Run Test 5's atomicity sub-test to verify.

2. **Idempotency edge cases.** Tests 6, 7, 8 cover the 200 / 404 / 409 paths. Reviewer additionally considers:
   - Rapid double-click acknowledge from a single browser tab → 200 / duplicate_ack row.
   - Concurrent ack from two browser tabs → first writer wins; second sees 200/duplicate_ack OR 409/late_ack depending on timing.
   - Ack of a never-created alert ID (typo, malformed UUID) → 404, no audit row.

3. **HealthMonitor doesn't lose alerts under load.** Event Bus has a drop-counter or similar pattern; reviewer verifies HealthMonitor's subscription doesn't bypass that pattern. If the Event Bus drops messages, the alert is silently lost — this is acceptable for 5a.1 (in-memory only) but flagged in close-out for 5a.2's persistence layer to address.

4. **No-operator case (banner stays visible indefinitely).** The spec says critical alerts requiring acknowledgment may stay visible if operator is absent. Reviewer confirms:
   - `acknowledgment_required_severities: ["critical"]` is the gate.
   - Auto-resolution policy (in 5a.2) determines whether `phantom_short_retry_blocked` and `cancel_propagation_timeout` ever auto-archive. Per the spec's policy table, both NEVER auto-resolve, so the banner stays visible indefinitely if operator absent. This is the intended behavior; reviewer flags it for operator awareness.

5. **In-memory state discipline.** Session 5a.1 is in-memory only; restart loses all alerts. Reviewer confirms the design doesn't rely on persistence anywhere in 5a.1; persistence-related logic is deferred to 5a.2.

6. **Subscription wiring.** Reviewer confirms the subscription line in `main.py` is co-located with other Event Bus subscriptions; no novel wiring pattern.

7. **AlertsConfig YAML loadability.** Reviewer verifies the YAML field is loadable (Pydantic strict mode) and that the default `["critical"]` produces the documented behavior.

## Sprint-Level Regression Checklist (for @reviewer)

- **Invariant 5:** PASS — expected ≥ 5,166.
- **Invariant 9 (IMPROMPTU-04 startup invariant unchanged):** PASS — Session 5a.1's `main.py` edit is the SystemAlertEvent subscription; the IMPROMPTU-04 fix is at a different location.
- **Invariant 14:** Row "After Session 5a.1" — Alert observability = "consumer + REST + ack (in-memory)".
- **Invariant 15:** PASS with scoped exception (5a.1 HealthMonitor consumer init).

## Sprint-Level Escalation Criteria (for @reviewer)

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **B1, B3, B4, B6** — standard halt conditions.
- **C5** (`main.py` edit scope) — high-risk site for invariant 9.
- **C7** (existing tests on HealthMonitor fail because the new consumer responsibility perturbs construction) — check `tests/core/test_health.py` if it exists.

---

*End Sprint 31.91 Session 5a.1 implementation prompt.*
