# Sprint 31.91, Session 5b: IBKR Emitter TODOs + End-to-End Integration Tests + Behavioral Alpaca Check

> **Track:** Alert Observability Backend (Session 5a.1 → 5a.2 → **5b**).
> **Position in track:** Third and final backend session. Wires the two pre-existing IBKR emitter TODO sites; verifies the full pipeline (emit → consume → REST/WS → ack → audit → auto-resolve) end-to-end; pins the Alpaca emitter site as deliberately unwired via behavioral anti-regression assertion.
> **Tier 3 #2 fires AFTER this session lands.** The combined 5a.1 + 5a.2 + 5b diff is the alert-observability seal.

## Pre-Flight Checks

1. **Read `.claude/rules/universal.md`.** RULE-038, RULE-050, RULE-019, RULE-007 all apply.

2. Read these files:
   - `argus/execution/ibkr_broker.py:453` — current TODO comment (disconnect / reconnect failure path).
   - `argus/execution/ibkr_broker.py:531` — current TODO comment (auth / permission failure path).
   - `argus/execution/ibkr_broker.py` — full file, to understand emitter context (where these failure paths sit relative to existing event publishing).
   - Sessions 5a.1 + 5a.2 deliverables on `main` (HealthMonitor consumer, REST endpoints, WebSocket fan-out, auto-resolution policy, persistence).
   - `argus/data/alpaca_data_service.py:593` — Alpaca emitter TODO. **Read for boundary awareness; do NOT modify.** Per MEDIUM #13, this site stays unwired until Sprint 31.94 retires Alpaca by deletion.
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D10 + AC-D10 (lines ~402-444, 666+).
   - Existing E2E test patterns in `tests/integration/`. Find one that exercises Event Bus → REST round-trip; use it as a structural template.

3. Run baseline (full suite):

   ```
   python -m pytest tests/ -n auto -q --ignore=tests/test_main.py
   ```

   Expected: green at Session 5a.2's count.

4. Branch: **`main`**. Verify Sessions 5a.1 + 5a.2 deliverables:

   ```bash
   grep -n "alert_state\|on_system_alert\|POLICY_TABLE\|rehydrate_alerts_from_db" argus/
   sqlite3 data/operations.db ".tables" | grep -E "alert_state|alert_acknowledgment|schema_version"
   ```

## Objective

Three deliverables:

1. **Resolve IBKR emitter TODO at `:453`** — emit `SystemAlertEvent(alert_type="ibkr_disconnect", severity="critical")` on Gateway disconnect / reconnect failure.
2. **Resolve IBKR emitter TODO at `:531`** — emit `SystemAlertEvent(alert_type="ibkr_auth_failure", severity="critical")` on API auth / permission failure.
3. **End-to-end integration tests** for all 4+ emitter sites through the full pipeline (5a.1 + 5a.2). **Includes the behavioral Alpaca anti-regression assertion** per MEDIUM #13.

## Requirements

### IBKR Emitter at `:453` (Gateway Disconnect / Reconnect Failure)

The existing TODO is a comment at the failure-handling site. Read the surrounding 30-50 lines to understand the structure. The pattern from spec D10:

```python
# BEFORE (the TODO site):
# TODO: emit SystemAlertEvent on disconnect/reconnect failure
self._logger.error("IBKR Gateway disconnect / reconnect failed: %s", err)

# AFTER (Sprint 31.91 Session 5b):
self._logger.error("IBKR Gateway disconnect / reconnect failed: %s", err)
alert = SystemAlertEvent(
    severity="critical",
    source="ibkr_broker.disconnect_handler",
    alert_type="ibkr_disconnect",
    message=(
        f"IBKR Gateway disconnect or reconnect failure: {err}. "
        f"Trading paused until connection recovered. "
        f"Auto-resolution: any successful subsequent IBKR operation."
    ),
    metadata={
        "error_message": str(err),
        "error_type": type(err).__name__,
        "detection_source": "ibkr_broker.disconnect_handler",
    },
)
self._event_bus.publish(alert)
```

The auto-resolution predicate (Session 5a.2 `IBKR_RECONNECT_PREDICATE`) consumes any `IBKRReconnectedEvent` OR `OrderFilledEvent` (any successful broker operation) — verify the predicate's actual signature in 5a.2 and align metadata if needed.

### IBKR Emitter at `:531` (Auth / Permission Failure)

Same pattern with `alert_type="ibkr_auth_failure"`:

```python
alert = SystemAlertEvent(
    severity="critical",
    source="ibkr_broker.auth_handler",
    alert_type="ibkr_auth_failure",
    message=(
        f"IBKR API auth/permission failure: {err}. "
        f"Trading paused until auth recovered. "
        f"Auto-resolution: any successful subsequent authenticated IBKR operation."
    ),
    metadata={
        "error_message": str(err),
        "error_type": type(err).__name__,
        "detection_source": "ibkr_broker.auth_handler",
    },
)
self._event_bus.publish(alert)
```

### Alpaca Emitter — DO NOT WIRE

`argus/data/alpaca_data_service.py:593` stays untouched. Per MEDIUM #13, the file is queued for retirement in Sprint 31.94 (DEF-178 + DEF-183). Wiring an emitter just to delete it 2 sprints later is wasted work AND introduces a risk window where Alpaca emits `SystemAlertEvent`s that the operator might mistake for actionable production signal.

The behavioral anti-regression test (Test 8 below) enforces this. Reading or referencing `:593` line numbers in tests is brittle to innocuous edits anywhere in the file; the behavioral assertion is robust.

### End-to-End Integration Tests (~8 new pytest + ~2 mock updates)

These tests exercise the full pipeline: emit → HealthMonitor consume → SQLite persist → REST `/active` returns it → WebSocket pushes it → operator ack via REST → audit-log writes → auto-resolve predicate fires → archive.

Use FastAPI's `TestClient` for REST + WebSocket; use the in-process Event Bus for emission.

1. **`test_ibkr_disconnect_reconnect_failure_emits_system_alert`** — trigger the IBKR Gateway failure path (mock `ib_async` to raise `ConnectionError`); assert `SystemAlertEvent(alert_type="ibkr_disconnect", severity="critical")` published.

2. **`test_ibkr_auth_permission_failure_emits_system_alert`** — same shape; trigger auth failure; assert `alert_type="ibkr_auth_failure"`.

3. **E2E: `test_e2e_databento_dead_feed_emit_consume_rest_ws_ack`** — emit `SystemAlertEvent(alert_type="databento_dead_feed")`; connect WS client; assert `alert_active` message received; `GET /alerts/active` returns it; ack via `POST /alerts/{id}/acknowledge`; assert `alert_acknowledged` WS message; assert `alert_acknowledgment_audit` SQLite row.

4. **E2E: `test_e2e_ibkr_disconnect_emit_consume_rest_ws_ack_auto_resolution`** — emit `ibkr_disconnect`; consume; ack OR allow auto-resolve via subsequent `IBKRReconnectedEvent`; assert auto_resolved status; assert WS pushes `alert_auto_resolved`; assert audit row with `outcome="auto_resolution"`.

5. **E2E: `test_e2e_phantom_short_emit_consume_rest_ws_ack_5_cycle_auto_resolution`** — emit `phantom_short` for AAPL; emit 5 `ReconciliationCompletedEvent`s with AAPL zero-shares; assert auto-resolved on cycle 5; assert WS + audit + REST `/history` all consistent. Specifically pin: the 5-cycle threshold matches `broker_orphan_consecutive_clear_threshold` from Session 2c.2.

6. **E2E: `test_e2e_acknowledgment_writes_audit_persists_restart`** — emit alert; ack; close DB; reopen DB (simulating restart with new HealthMonitor); call `rehydrate_alerts_from_db`; assert acknowledged state survives; query `alert_acknowledgment_audit` directly; assert row present.

7. **E2E: `test_e2e_phantom_short_retry_blocked_never_auto_resolves`** — emit `phantom_short_retry_blocked`; emit 100 `ReconciliationCompletedEvent`s; assert alert is STILL `active` (never auto-resolves); operator-ack via REST; assert moves to `acknowledged`. This pins the policy-table NEVER row for the alert type Session 3 introduced.

8. **Behavioral anti-regression: `test_alpaca_data_service_does_not_emit_system_alert_events`** —

   ```python
   def test_alpaca_data_service_does_not_emit_system_alert_events():
       """Sprint 31.91 boundary: Alpaca emitter site stays unwired
       until Sprint 31.94 retires the broker by deletion (DEF-178/183).

       Behavioral check (replaces line-number-based textual check from
       earlier sprint drafts): inspects the actual module source for
       any reference to SystemAlertEvent. Robust to refactors;
       enforces the architectural constraint at semantic level."""
       import inspect
       import argus.data.alpaca_data_service as mod
       src = inspect.getsource(mod)
       assert "SystemAlertEvent" not in src, (
           "Alpaca data service should not emit SystemAlertEvent — "
           "queued for retirement in Sprint 31.94 (DEF-178/183). "
           "If the emitter was added intentionally, this test must be "
           "removed AS PART OF the retirement sprint, not separately."
       )
   ```

   The test failure message tells a future maintainer exactly what to do: don't suppress the assertion; remove it together with the file.

**Mock updates (~2):** test fixtures that mock `IBKRBroker` may need to expose the new emit-on-failure path. Update `conftest.py` factory.

## Definition of Done

- [ ] `:453` emitter resolved with full alert metadata payload.
- [ ] `:531` emitter resolved with full alert metadata payload.
- [ ] `argus/data/alpaca_data_service.py` ZERO edits (do-not-modify; verified by `git diff --stat`).
- [ ] 8 E2E + emitter tests + 2 mock updates added; all green.
- [ ] Behavioral anti-regression test pins Alpaca abstinence semantically.
- [ ] Test 5 specifically pins the 5-cycle threshold = Session 2c.2's `broker_orphan_consecutive_clear_threshold`.
- [ ] Test 7 specifically pins the NEVER row for `phantom_short_retry_blocked`.
- [ ] CI green; pytest baseline ≥ Session 5a.2 + 8.
- [ ] Tier 2 review (backend safety reviewer) verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-5b-closeout.md`.
- [ ] **Tier 3 architectural review #2 invoked** on combined 5a.1 + 5a.2 + 5b diff (operator-triggered post-merge; see escalation-criteria.md §A1.5).

## Close-Out Report

Standard structure plus:

- **Tier 3 #2 invocation pre-amble:** the close-out should explicitly state "Sessions 5a.1 + 5a.2 + 5b are now on `main`. Operator: invoke Tier 3 #2 architectural review on combined diff before proceeding to Session 5c."
- **Pipeline coverage matrix:** table showing each emitter type × each pipeline stage (REST `/active`, WebSocket push, ack flow, audit-log persistence, auto-resolution). Tests 3-7 should fill this table; visualize gaps if any.
- **Alpaca abstinence rationale:** restate the MEDIUM #13 disposition for posterity.

```json
{
  "session": "5b",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 8,
  "ibkr_emitters_resolved": [453, 531],
  "alpaca_behavioral_anti_regression_passes": true,
  "tier3_2_ready": true
}
```

## Tier 2 Review Invocation

Standard pattern. Backend safety reviewer template.

Reviewer output: `docs/sprints/sprint-31.91-reconciliation-drift/session-5b-review.md`.

## Session-Specific Review Focus

1. **Behavioral Alpaca anti-regression robustness.** Reviewer reads the test. Verifies it uses `inspect.getsource` (not text grep on a known line) — robust to refactors. Verifies the failure message points at the right rationale (DEF-178/183, Sprint 31.94 retirement).

2. **E2E coverage matrix complete.** Reviewer fills in the pipeline-coverage table from the close-out. Each emitter × each stage; gaps are CONCERNS.

3. **5-cycle threshold cross-reference.** Test 5 uses `broker_orphan_consecutive_clear_threshold`. If the test hardcodes `5`, that's a CONCERN — single-source-of-truth means reading the config field, then asserting cycle count.

4. **NEVER auto-resolve enforcement.** Test 7 emits 100 events; alert stays active. Reviewer reads the test; if "100" is "1" in disguise (e.g., `for _ in range(1)` typo), the test is meaningless. Should be a noticeably large number that proves "across many cycles, no resolution."

5. **`:1670-1750` IMPROMPTU-04 fix unchanged.** Sanity check; this session is in `ibkr_broker.py` (a different file from `order_manager.py`), but git diff covers everything.

6. **Tier 3 #2 invocation timing.** Reviewer verifies the close-out explicitly tells operator to invoke Tier 3 #2 BEFORE Session 5c. If the close-out goes straight to "next: Session 5c," that's a CONCERN — Tier 3 #2 is a phase boundary.

## Sprint-Level Regression Checklist

- **Invariant 1:** PASS.
- **Invariant 5:** PASS — expected ≥ Session 5a.2 + 8.
- **Invariant 14:** Row "After Session 5b" — Alert observability = "full pipeline E2E verified; backend complete".
- **Invariant 16 (Alpaca abstinence):** PASS — verified by Test 8.
- **Invariant 15:** PASS.

## Sprint-Level Escalation Criteria

- **A1.5** (Tier 3 #2 ESCALATE) — fired AFTER this session by the operator.
- **A2** (Tier 2 CONCERNS or ESCALATE).
- **B1, B3, B4, B6** — standard.
- **C7** (E2E tests pull in event-bus + REST + WS + SQLite together; flakes in any layer can cascade — investigate the layer, not the test).

---

*End Sprint 31.91 Session 5b implementation prompt.*
