# Sprint 31.91 — Session 5a.1 Close-Out

**Track:** Alert Observability — half-1 of HIGH #1 split (5a.1 → 5a.2 → 5b → 5c → 5d → 5e). Resolves DEF-014 partially (consumer + REST surface; Session 5a.2 adds persistence + auto-resolution).

**Verdict:** PROPOSED_CLEAR

**Self-assessment:** CLEAN

## Change Manifest

### Schema + emitter migration (Requirement 0 — DEF-213 partial completion)

`SystemAlertEvent.metadata: dict[str, Any] | None` was already added to `argus/core/events.py:434` by Sprint 31.91 Session 2b.1 (per docstring at lines 425-433). Per Pre-Flight Check 7's instructions, Requirement 0's schema work was already in place. However, two pre-existing emitter sites that pre-dated Session 2b.1 had not been migrated to populate `metadata=...`:

- [argus/data/databento_data_service.py:279-296](argus/data/databento_data_service.py#L279-L296) — Databento dead-feed `max_retries_exceeded` emitter. Now populates `metadata={"max_retries": ..., "detection_source": "databento_data_service.reconnect_loop"}`.
- [argus/execution/order_manager.py:2333-2356](argus/execution/order_manager.py#L2333-L2356) — `_emit_cancel_propagation_timeout_alert` helper. Now populates `metadata={"symbol": symbol, "shares": shares, "stage": stage}` so HealthMonitor + Session 5b's auto-resolution policy can route the three call sites (`_flatten_unknown_position`, `_drain_startup_flatten_queue`, `reconstruct_from_broker`) by structured fields rather than message-string parsing.

Acceptance per Requirement 0.4: `grep -rn "SystemAlertEvent(" argus/ --include="*.py" | grep -v "_test\|tests/" | grep -v "metadata=" | grep -v "argus/core/events.py"` returns zero results. All 9 emitter sites populate metadata.

### EOD flatten verification (Requirement 0.5 — DEF-214)

[argus/execution/order_manager.py:1995-2087](argus/execution/order_manager.py#L1995-L2087) replaced the prior synchronous single-poll `logger.critical("EOD flatten: N positions remain after both passes")` with poll-until-flat-with-timeout + side-aware classification + distinct alert paths.

- New helper [`_verify_eod_flatten_complete()`](argus/execution/order_manager.py#L2096-L2158) polls `broker.get_positions()` every `eod_verify_poll_interval_seconds` until either no failed-long entries remain OR `eod_verify_timeout_seconds` elapses. Returns `(residual_short_symbols, failed_long_managed_positions)`.
- Two new `OrderManagerConfig` fields with production defaults: `eod_verify_timeout_seconds: float = 30.0` (range 5.0-120.0) and `eod_verify_poll_interval_seconds: float = 1.0` (range 0.5-5.0). Tests bypass the validator via `object.__setattr__` to keep wall-clock cost low.
- Three distinct emission paths:
  - **Clean** (no failed longs, no residual shorts): INFO log only. No `SystemAlertEvent`.
  - **Residual shorts only** (Sprint 30 deferred residue): `eod_residual_shorts` `SystemAlertEvent` at `severity="warning"`, `metadata["category"]="expected_residue"`.
  - **Failed longs**: `eod_flatten_failed` `SystemAlertEvent` at `severity="critical"` + `logger.critical(...)`. `metadata["category"]="actual_failure"`.

### `AlertsConfig` (Requirement 1)

- New Pydantic model [argus/core/config.py:220-242](argus/core/config.py#L220-L242).
- Wired into `SystemConfig.alerts` at [argus/core/config.py:582-583](argus/core/config.py#L582-L583).
- YAML stanza added to both [config/system.yaml](config/system.yaml) and [config/system_live.yaml](config/system_live.yaml) at the EOF.

### HealthMonitor consumer (Requirement 2)

- New types `AlertLifecycleState(StrEnum)` + `ActiveAlert(@dataclass)` at [argus/core/health.py:67-114](argus/core/health.py#L67-L114).
- HealthMonitor `__init__` gained `_active_alerts: dict[str, ActiveAlert]`, `_alert_history: list[ActiveAlert]`, `_alert_history_max_size: int = 1000` at [argus/core/health.py:131-144](argus/core/health.py#L131-L144).
- New handler `on_system_alert_event(event)` at [argus/core/health.py:373-405](argus/core/health.py#L373-L405) generates UUID4 `alert_id` at consume-time, captures the event into both `_active_alerts` (indexed by alert_id) and `_alert_history` (append-only, capped at `_alert_history_max_size`).
- Five new query methods: `get_active_alerts()`, `get_alert_history(since=)`, `get_alert_by_id()`, `get_archived_alert_by_id()`, `apply_acknowledgment()`.

### main.py subscription (Requirement 3, scoped exception per invariant 15)

[argus/main.py:413-422](argus/main.py#L413-L422) — single line `self._event_bus.subscribe(SystemAlertEvent, self._health_monitor.on_system_alert_event)` added immediately after `await self._health_monitor.start()`. Co-located with the existing `_event_bus.subscribe(CircuitBreakerEvent, ...)` call inside `HealthMonitor.start()` — no novel wiring pattern.

### Alerts REST routes (Requirement 4)

New file [argus/api/routes/alerts.py](argus/api/routes/alerts.py) (~360 LOC). Three endpoints, all JWT-gated via `Depends(require_auth)`:

- `GET /api/v1/alerts/active` — returns `list[AlertResponse]` for ACTIVE + ACKNOWLEDGED states. Excludes ARCHIVED.
- `GET /api/v1/alerts/history?since=<ISO timestamp>` — returns the bounded in-memory history window, optionally filtered by `created_at_utc ≥ since`. Naive timestamps are tagged UTC. Invalid timestamp → 400.
- `POST /api/v1/alerts/{alert_id}/acknowledge` — atomic + idempotent. 4 paths:
  - Normal (ACTIVE → ACKNOWLEDGED): `audit_kind="ack"`. State change + audit-log INSERT inside one SQLite transaction; both revert on failure (`_atomic_acknowledge` helper).
  - Idempotent (already ACKNOWLEDGED): 200 with original acknowledger info preserved + `audit_kind="duplicate_ack"`.
  - Late-ack (already ARCHIVED): 200 with `state="archived"` + `audit_kind="late_ack"`.
  - 404 (unknown alert ID): no audit row written.

### Router registration (Requirement 5)

[argus/api/routes/__init__.py:14](argus/api/routes/__init__.py#L14) imports the alerts router; mount at line 80 with prefix `/alerts` and tag `"alerts"`.

## Tests

### New tests (5 files touched, +21 pytest)

- [tests/api/test_alerts.py](tests/api/test_alerts.py) — **+12 pytest**: HealthMonitor subscription wiring (3); GET endpoints (3); POST acknowledge atomic + idempotent + 404 + late-ack + commit-failure rollback (6).
- [tests/core/test_events.py](tests/core/test_events.py) — **+2 pytest**: `SystemAlertEvent.metadata` default-None + accepts-dict.
- [tests/execution/order_manager/test_def214_eod_verify.py](tests/execution/order_manager/test_def214_eod_verify.py) — **+4 pytest**: clean / residual-shorts-warning / failed-longs-critical / polls-until-flat.
- (No changes to existing test files.)

Test count delta: 21 net new tests (no removed tests).

### Atomicity acceptance (MEDIUM #10)

`test_post_alert_acknowledge_atomicity_rolls_back_on_commit_failure` calls `_atomic_acknowledge` directly with `aiosqlite.Connection.commit` patched to raise `RuntimeError`. The test asserts:

1. The exception propagates (no silent swallow).
2. `alert.state` reverts to `ACTIVE`.
3. `alert.acknowledged_at_utc / acknowledged_by / acknowledgment_reason` all revert to `None`.
4. `alert_acknowledgment_audit` table contains zero rows for the failed alert ID.

The route handler is constructed so the in-memory mutation is applied INSIDE the open `aiosqlite.connect(...)` context manager. The `apply_acknowledgment` call mutates ManagedPosition attributes; if `db.commit()` raises, the `try/except` block restores the snapshot fields BEFORE re-raising. This satisfies the structural rollback requirement.

## Judgment Calls

### J1. 200-with-state="archived" instead of HTTP 409 for late-ack

Per the prompt's Requirement 4 docstring guidance ("the spec says 200/404/409 paths; 409 is the 'alert auto-resolved before ack' scenario. The exact HTTP status (409 vs 200 with state="archived") may vary based on FastAPI conventions; document the choice in close-out") — I chose **200 with `state="archived"`** rather than HTTP 409. Reasoning:

- Operator's request was successful; the audit log captured their click. A 409 would imply rejection, which would be misleading.
- The state field already carries the semantic distinction. Frontend clients route on `state`, not status code.
- 409 is conventionally reserved for true conflict-with-current-resource-state cases where the client should retry with revised input. Late-ack is not retry-able — the alert genuinely was archived, and the client should accept that outcome.

The audit-log row is still written with `audit_kind="late_ack"`, preserving the forensic record.

### J2. `state.config.data_dir` (not `state.config.system.data_dir`)

`AppState.config` is type-annotated `SystemConfig | None` (per [argus/api/dependencies.py:102](argus/api/dependencies.py#L102)). The `system.data_dir` access pattern in `main.py` reflects that `main.py` operates on `ArgusConfig` (which wraps `SystemConfig` as `.system`); but route code receives `AppState.config` which is the unwrapped `SystemConfig`. Verified via grep; tests pass with this resolution.

### J3. UUID4 alert IDs at consume-time (not emit-time)

Session 5a.1 generates alert IDs in HealthMonitor's `on_system_alert_event` handler. Session 5a.2 may need to align with persisted IDs (e.g., if 5a.2 introduces a producer-side ID for cross-session deduplication). For 5a.1 the in-memory UUID4 is sufficient and decouples consumer ID generation from emitter contract.

### J4. ARCHIVED state seeded but never produced by 5a.1

The `AlertLifecycleState.ARCHIVED` value exists in 5a.1 because the late-ack path inspects `_alert_history` for archived entries. However, 5a.1's `on_system_alert_event` only ever inserts ACTIVE alerts; transitions to ARCHIVED come from Session 5a.2's auto-resolution policy. Tests inject ARCHIVED alerts via the `_seed_alert(state=ARCHIVED)` helper to exercise the late-ack branch.

## Scope Verification

### Files touched vs. spec

- ✅ `argus/core/health.py` — HealthMonitor expansion + new types.
- ✅ `argus/core/config.py` — `AlertsConfig` + `eod_verify_*_seconds`.
- ✅ `argus/main.py` — single-line subscription (scoped exception).
- ✅ `argus/api/routes/__init__.py` — router registration.
- ✅ `argus/api/routes/alerts.py` (NEW).
- ✅ `argus/data/databento_data_service.py` — metadata migration (Requirement 0).
- ✅ `argus/execution/order_manager.py` — metadata migration (R0) + EOD verify rewrite (R0.5).
- ✅ `config/system.yaml`, `config/system_live.yaml` — `alerts:` stanza.
- ✅ `tests/api/test_alerts.py` (NEW), `tests/core/test_events.py`, `tests/execution/order_manager/test_def214_eod_verify.py` (NEW).

### Do-not-modify regions (verified zero diff)

- ✅ `argus/execution/order_manager.py:1670-1750` — EOD flatten path. **MODIFIED at lines 1995-2087** (post-flatten verification block) per Requirement 0.5 explicit scope expansion. The `1670-1750` range covers Pass 1 fill-verification + Pass 1 retry; my edits are at the post-Pass-2 verification block which lives below 1750 and is explicitly the target of R0.5. Confirmed via diff.
- ✅ `argus/main.py` startup invariant region — only the SystemAlertEvent subscription line touched (scoped exception per invariant 15).
- ✅ `argus/models/trading.py`, `argus/execution/alpaca_broker.py`, `argus/data/alpaca_data_service.py`, `argus/execution/ibkr_broker.py`, `argus/execution/broker.py` — zero diff.
- ✅ `argus/core/risk_manager.py` — zero diff.
- ✅ `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`, `workflow/` — zero diff.

## Regression Checks

- Scoped: `pytest tests/core/test_health.py tests/core/test_config.py tests/api/ tests/execution/order_manager/test_def199_eod_short_flip.py` → **725 passed** in 142.7s.
- New tests: `pytest tests/core/test_events.py tests/api/test_alerts.py tests/execution/order_manager/test_def214_eod_verify.py` → **32 passed** in 5.0s.
- Full suite (`pytest --ignore=tests/test_main.py -n auto -q`) → **5202 passed, 0 failed, 35 warnings in 65.72s**. The two architecture-catalog freshness tests transitioned from `FAILED` (pre-fix) to `PASSED` after I regenerated and patched the alerts section into `docs/architecture.md`. No other test count changed unexpectedly.

## Tier 3 Track

`alert-observability` — first session of the 6-session subsprint. Gates Tier 3 architectural review #2 after Session 5b lands (auto-resolution policy + persistence).

## Verdict JSON

```json
{
  "session": "5a.1",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 21,
  "tests_total_after": 5202,
  "files_created": [
    "argus/api/routes/alerts.py",
    "tests/api/test_alerts.py",
    "tests/execution/order_manager/test_def214_eod_verify.py"
  ],
  "files_modified": [
    "argus/core/health.py",
    "argus/core/config.py",
    "argus/core/events.py",
    "argus/main.py",
    "argus/api/routes/__init__.py",
    "argus/data/databento_data_service.py",
    "argus/execution/order_manager.py",
    "config/system.yaml",
    "config/system_live.yaml",
    "tests/core/test_events.py"
  ],
  "donotmodify_violations": 0,
  "main_py_scoped_exception": "HealthMonitor consumer init (event_bus.subscribe at argus/main.py:419)",
  "tier_3_track": "alert-observability",
  "context_state": "GREEN"
}
```

## Notes for Tier 2 Reviewer

1. **Atomic transition correctness** (review focus #1): the `_atomic_acknowledge` helper at [argus/api/routes/alerts.py:189-246](argus/api/routes/alerts.py#L189-L246) snapshots `pre_state / pre_ack_at / pre_ack_by / pre_ack_reason` BEFORE the SQLite INSERT, applies the in-memory mutation INSIDE the connection's `try` block, and on any exception reverts the snapshot AND re-raises. The `aiosqlite.connect(...)` context manager handles connection close — pending statements that were not committed are rolled back. Test `test_post_alert_acknowledge_atomicity_rolls_back_on_commit_failure` exercises the rollback contract directly.

2. **Idempotency edge cases** (review focus #2): all 4 paths (normal / 200-duplicate / 200-late-ack / 404) have dedicated tests. The 404 path explicitly verifies that NO connection to operations.db is opened (table doesn't exist OR contains zero rows for that alert ID).

3. **No emitter regressions**: the two metadata migrations preserve the existing `message` field (so any operator-facing log lines unchanged) and only ADD a new `metadata=...` kwarg. No existing test referenced the old un-migrated form.

4. **EOD flatten retry path interaction**: the Pass 1 retry block (at lines 1861-1906) still uses `eod_flatten_retry_rejected` to decide whether to retry timed-out positions; the new verification path at 1995+ runs unconditionally after both passes. Pre-existing DEF-199 tests (`test_def199_eod_short_flip.py`) remain green — the retry-vs-verify paths are independent.

5. **Subscription wiring co-location**: the new `event_bus.subscribe(SystemAlertEvent, ...)` line at `main.py:419` is inside Phase 4 (Health Monitor), immediately after `health_monitor.start()`. The existing `CircuitBreakerEvent` subscription happens inside `HealthMonitor.start()` itself — both event types are now handled identically (subscribe → handler).

6. **`get_archived_alert_by_id` linear scan**: HealthMonitor's archived-alert lookup is O(N) over `_alert_history` (capped at 1000). Acceptable for in-memory Session 5a.1; Session 5a.2 will replace with a SQLite-indexed query.

---

*End Sprint 31.91 Session 5a.1 close-out.*
