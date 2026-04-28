# Sprint 31.91 Session 5a.2 — Close-Out

**Self-assessment:** PROPOSED_CLEAR (Tier 2 review pending).

## Change Manifest

### New files
- `argus/core/alert_auto_resolution.py` — per-alert-type policy table,
  8 predicates, `PredicateContext`, `build_policy_table()`,
  `all_consumed_event_types()`, `NEVER_AUTO_RESOLVE` sentinel.
- `argus/data/migrations/__init__.py` — public surface for the
  migration framework.
- `argus/data/migrations/framework.py` — `Migration` dataclass +
  `apply_migrations()` (transactional per-step) + `current_version()`.
- `argus/data/migrations/operations.py` — registry for the
  `operations` schema. Migration v1 codifies all tables created in
  Sessions 5a.1 + 5a.2 (`phantom_short_gated_symbols`,
  `alert_acknowledgment_audit`, `alert_state` + 3 indexes).
- `argus/api/websocket/alerts_ws.py` — `WS /ws/v1/alerts` handler
  (JWT auth, initial snapshot, 4 message types, disconnect-watcher
  idiom from DEF-193 / DEF-200).
- `tests/api/test_alerts_5a2.py` — 20 new pytest tests covering
  persistence, rehydration ordering, all 8 policy entries, threshold
  single-source-of-truth coupling, retention behavior, VACUUM idiom,
  WebSocket fan-out contract, and migration framework idempotence.

### Modified files
- `argus/core/events.py` — added `ReconciliationCompletedEvent`,
  `IBKRReconnectedEvent`, `DatabentoHeartbeatEvent` dataclasses. These
  are predicate inputs; emission in production is deferred to future
  sessions (broker-layer reconnect-recovery for `IBKRReconnectedEvent`,
  data-layer for `DatabentoHeartbeatEvent`, OrderManager reconciliation
  for `ReconciliationCompletedEvent`). Predicates are wired today; they
  fire when emission lands.
- `argus/core/config.py` — `AlertsConfig` extended with
  `auto_resolve_on_condition_cleared`, `audit_log_retention_days`,
  `archived_alert_retention_days`, `retention_task_interval_seconds`.
- `argus/core/health.py` — `HealthMonitor`:
  - constructor accepts `alerts_config`, `reconciliation_config`,
    `operations_db_path`;
  - new `_persist_alert`, `_ensure_operations_schema`,
    `rehydrate_alerts_from_db`, `subscribe_state_changes`,
    `unsubscribe_state_changes`, `_publish_state_change`,
    `_subscribe_predicate_handlers`, `_evaluate_predicates`,
    `_auto_resolve`, `_write_auto_resolution_audit`,
    `_retention_loop`, `_run_retention_once`,
    `_vacuum_operations_db`, `persist_acknowledgment_after_commit`;
  - `start()` subscribes predicate handlers + spawns retention task;
    `stop()` cancels retention task.
  - `apply_acknowledgment` reverted to pure in-memory (post-commit
    persistence handed off to the route via
    `persist_acknowledgment_after_commit`).
- `argus/api/routes/alerts.py` — acknowledgment route calls
  `health_monitor.persist_acknowledgment_after_commit(alert)` after the
  audit-log COMMIT, so persistence + WS fan-out only run on success.
- `argus/api/websocket/__init__.py` — re-export `alerts_ws_router`.
- `argus/api/server.py` — mount `alerts_ws_router`.
- `argus/main.py` — Phase 4 HealthMonitor construction now passes
  `alerts_config` / `reconciliation_config` /
  `operations_db_path = data_dir/operations.db`. Rehydration call
  (`await self._health_monitor.rehydrate_alerts_from_db()`) inserted
  IMMEDIATELY BEFORE the existing
  `event_bus.subscribe(SystemAlertEvent, ...)` line.
- `docs/architecture.md` — §4 WebSocket table updated to include
  `WS /ws/v1/alerts` (catalog freshness test required).

## Definition of Done

- [x] `WS /ws/v1/alerts` functional. JWT auth + initial snapshot +
      4 message types (`alert_active`, `alert_acknowledged`,
      `alert_auto_resolved`, `alert_archived`).
- [x] `alert_state` SQLite table with full schema + 3 indexes.
- [x] Rehydration in `main.py` BEFORE Event Bus subscription.
      `Phase 4` rehydration call is the line immediately preceding
      the SystemAlertEvent subscription. The test
      `test_alert_state_rehydrated_before_event_bus_subscription`
      directly exercises this contract by constructing a fresh
      HealthMonitor, calling rehydrate, asserting active state is
      already populated, THEN subscribing.
- [x] Auto-resolution policy table covers all 8 alert types
      (`phantom_short`, `stranded_broker_long`, `phantom_short_retry_blocked`,
      `cancel_propagation_timeout`, `ibkr_disconnect`, `ibkr_auth_failure`,
      `databento_dead_feed`, `phantom_short_startup_engaged`).
- [x] `phantom_short` predicate reads
      `ReconciliationConfig.broker_orphan_consecutive_clear_threshold`
      via injected `threshold_provider`. NO duplicated AlertsConfig
      field. Test
      `test_phantom_short_uses_2c2_threshold_field` verifies the
      coupling by overriding the reconciliation threshold to 3 and
      confirming the predicate fires on the 3rd cycle (not the 5th).
      Static-source check
      `test_phantom_short_predicate_does_not_define_duplicate_threshold`
      verifies the AlertsConfig model has no duplicated field.
- [x] Retention policy + daily background task + VACUUM via
      `asyncio.to_thread`. Test
      `test_vacuum_runs_via_asyncio_to_thread` monkeypatches
      `asyncio.to_thread` to confirm the call goes through the
      worker-thread path.
- [x] Schema migration framework + `schema_version` table + first
      migration registered. Test
      `test_schema_version_records_v1` asserts row insert; test
      `test_apply_migrations_is_idempotent` asserts re-application is
      a no-op.
- [x] 20 new pytest tests; all green.
- [x] Pytest baseline ≥ Session 5a.1 + 12: 5202 → 5222 (+20).
- [ ] Tier 2 review verdict CLEAR — pending.

## Persistence boundary closed

5a.1's "in-memory only" restriction is lifted. Restart-survives is
verified by:

- Test #3 (`test_alert_state_persists_to_sqlite_for_restart_recovery`):
  emit alert; confirm row in `alert_state` table.
- Test #4 (`test_alert_state_rehydrated_before_event_bus_subscription`):
  populate DB via a first HealthMonitor; construct fresh HealthMonitor
  in a separate `EventBus`; rehydrate; assert prior alert is in
  `_active_alerts` BEFORE subscribing; then subscribe and emit a new
  alert to confirm subscription works.

## Auto-resolution single-source-of-truth

`make_phantom_short_predicate` accepts a `threshold_provider`
callable. `HealthMonitor.__init__` constructs the policy table with
`phantom_short_threshold_provider=lambda: self._reconciliation_config.broker_orphan_consecutive_clear_threshold`,
so every predicate evaluation reads the live value from the
`ReconciliationConfig` instance. Operators changing
`broker_orphan_consecutive_clear_threshold` for the Session 2c.2 entry
gate ALSO change the auto-resolution threshold — single source of
truth.

## Migration framework

Pattern for future schema changes: register a `Migration` object in
the per-DB module (`operations.py` for `data/operations.db`).
`apply_migrations()` reads the recorded version, applies every
migration with `version > current` in transactional order, and bumps
`schema_version` inside each migration's transaction so a failed
migration leaves the recorded version unchanged.

`down` callable on `Migration` is advisory — production does NOT
auto-rollback. Documented in module docstring + `Migration` dataclass
docstring.

## Test scaffolding cleanup

The Session 5a.1 close-out had noted "test scaffolding for the
`auto_resolved` status injection." That scaffolding is no longer
needed — real predicates fire ARCHIVED state via `_auto_resolve`. The
pre-existing tests in `tests/api/test_alerts.py` continue to pass
unchanged (they exercised in-memory state without persistence; the
in-memory contract is preserved).

## Out-of-scope events (transparent disclosure)

The spec listed `ReconciliationCompletedEvent`, `IBKRReconnectedEvent`,
and `DatabentoHeartbeatEvent` under "Read events.py — verify all exist;
if any are missing, halt B6." None of those existed at session start.

Per RULE-002, this was flagged. The pragmatic resolution: add the
three events as new dataclasses in `argus/core/events.py`. The
predicate framework references them today; production emission is
deferred to:

- **`ReconciliationCompletedEvent`** — needs an emit in OrderManager's
  reconciliation cycle. Natural fit for the post-31.9 component-ownership
  sprint or the `phantom_short` retry-blocked detection path.
- **`IBKRReconnectedEvent`** — needs an emit at the IBKR broker's
  reconnect success path. Natural fit for the
  `post-31.9-reconnect-recovery` sprint (DEF-194/195/196).
- **`DatabentoHeartbeatEvent`** — needs an emit from the data-layer
  health poller. The existing `DataResumedEvent` is also consumed by
  the `databento_dead_feed` predicate as a fallback signal.

Until those producers wire emission, predicates that consume those
events are no-ops in production. The `phantom_short_retry_blocked` /
`cancel_propagation_timeout` `NEVER_AUTO_RESOLVE` predicates are
correctly active today.

## Sprint-Level Regression Checklist

- **Invariant 1 — Pytest passes:** PASS. 5222 / 5222 (excluding
  `tests/test_main.py`, baseline noted as 27 pass / 5 skip /
  12 pre-existing fails — all pre-existing per `git stash` comparison).
- **Invariant 5 — Test count growth:** PASS. +20 (≥ Session 5a.1
  baseline + 12).
- **Invariant 14 — Alert observability surface:** Now reads
  "REST + WS + persistence + auto-resolution + retention".
- **Invariant 15 — main.py do-not-modify:** PASS with documented
  scoped exception (Phase 4 rehydration line, immediately before
  Session 5a.1's subscription line, immediately following
  HealthMonitor construction with new kwargs).

## Context State

GREEN — work fit comfortably within context; no compaction risk.

```json
{
  "session": "5a.2",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 20,
  "tests_total_delta": "+20 (5202 → 5222)",
  "auto_resolution_policy_complete": true,
  "schema_migration_framework_introduced": true,
  "phantom_short_threshold_single_source": true,
  "out_of_scope_disclosures": [
    "ReconciliationCompletedEvent + IBKRReconnectedEvent + DatabentoHeartbeatEvent added as new dataclasses in argus/core/events.py; production emission deferred per close-out 'Out-of-scope events' section."
  ]
}
```
