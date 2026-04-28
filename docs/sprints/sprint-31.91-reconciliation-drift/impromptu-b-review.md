# Sprint 31.91 — Impromptu B Tier 2 Review

> **Track:** Alert Observability Backend Hardening (post-Tier-3-#2).
> **Tier 3 track marker:** `alert-observability`.
> **Reviewing:** DEF-221 (DatabentoHeartbeatEvent producer wiring) + DEF-217 end-to-end validation.
> **Implementation closeout:** `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-b-closeout.md`.
> **Anchor commit (pre-impromptu HEAD):** `bb02174` on `main`.
> **Verdict:** **CLEAR** — three LOW/INFO observations recorded; none blocking.

---

## Verdict (Structured JSON)

```json
{
  "schema_version": "1.0",
  "sprint": "31.91",
  "session": "Impromptu-B",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "Recovery transition is tested by directly setting `service._stale_published = False` rather than driving a real DataResumedEvent flow through `_stale_data_monitor`. The predicate's `DataResumedEvent` branch in `_databento_heartbeat_predicate` is therefore not exercised by this E2E test (covered elsewhere in unit-level tests and `TestE2EDatabentoDeadFeed`).",
      "severity": "LOW",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/integration/test_alert_pipeline_e2e.py",
      "recommendation": "Acceptable for this impromptu's scope. Future test-hygiene pass could add a variant that drives Stale→Resumed via the natural state-monitor flow."
    },
    {
      "description": "Pre-existing `Task was destroyed but it is pending!` warning for `_log_post_start_symbology_size` (scheduled via `asyncio.ensure_future` at databento_data_service.py:392 and not tracked by start()/stop()). Surfaces in the new test's teardown but is not introduced by this impromptu — same pattern exists across the existing data-service tests.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/data/databento_data_service.py",
      "recommendation": "Out of scope for Impromptu B. Could be addressed in a future component-ownership cleanup (DEF-202 sibling — long-lived task lifecycle hygiene)."
    },
    {
      "description": "The suppression assertion at lines 1133-1139 depends on `start()` and `_connect_live_session()` not resetting `_stale_published` after the test pre-engages it. This is correct today (only `_stale_data_monitor` writes the flag), and the production-side docstring at `_heartbeat_publish_loop` documents the ownership invariant — so the contract is protected, but the test does not have its own guard against a future regression that pre-clears the flag in start().",
      "severity": "INFO",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/integration/test_alert_pipeline_e2e.py",
      "recommendation": "None required. The production-side docstring is the canonical guard."
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All Definition-of-Done items satisfied. Config field added with correct constraints (gt=0.0, le=300.0). _heartbeat_publish_loop spawned in start() step 8; cancelled in stop() with CancelledError suppression, parallel to the three sibling tasks. Suppression contract verified via the test's pre-engagement of _stale_published and the captured-count diff. End-to-end test drives `_run_with_reconnection` to exhaustion and asserts the literal `databento_dead_feed` round-trips (DEF-217 production-path regression guard). Heartbeat interval configurable via DatabentoConfig and patched to 0.05s in the test. No regression in existing Databento data-service tests (101 passed). Full suite green at 5,238 tests.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-b-databento-heartbeat-impl.md",
    "docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md",
    "argus/core/config.py",
    "argus/data/databento_data_service.py",
    "tests/integration/test_alert_pipeline_e2e.py",
    "argus/core/alert_auto_resolution.py",
    "argus/core/events.py",
    "tests/mocks/mock_databento.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 5238,
    "new_tests_adequate": true,
    "test_quality_notes": "The new E2E test is genuinely end-to-end — it instantiates a real DatabentoDataService, mocks the Databento module at sys.modules level (RULE-047 pattern), drives `_run_with_reconnection` through to retries-exhausted, captures the resulting SystemAlertEvent through HealthMonitor's state-change queue, and asserts the load-bearing `alert_type='databento_dead_feed'` literal. This is the FIRST test in the E2E file that drives the production emitter chain instead of fabricating SystemAlertEvent — it is the regression guard DEF-217 needed. The suppression assertion is falsifiable: a regression that drops the `if self._stale_published: continue` branch would publish heartbeats during the dead-feed window and the assertion would fire. Heartbeat-count assertion (≥3) matches the predicate threshold (>=3 healthy heartbeats at alert_auto_resolution.py:190). Audit-row assertion (audit_kind='auto_resolution', operator_id='auto') confirms the auto-resolution path vs operator-ack."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      { "check": "Diff touches only the 3 in-scope files (config.py, databento_data_service.py, test_alert_pipeline_e2e.py)", "passed": true, "notes": "Verified via `git diff HEAD --name-only`." },
      { "check": "No edits to alpaca_data_service.py, order_manager.py, ibkr_broker.py, main.py, events.py, alert_auto_resolution.py, or migration framework", "passed": true, "notes": "Confirmed by file-list verification." },
      { "check": "No new state attribute introduced — heartbeat task reuses `_running` and `_stale_published`", "passed": true, "notes": "Only new attributes are `_heartbeat_publish_task` (asyncio.Task handle, not state) and the `heartbeat_publish_interval_seconds` config field." },
      { "check": "Task spawn + cancel + await pattern matches the three sibling tasks (_stream_task, _stale_monitor_task, _heartbeat_task)", "passed": true, "notes": "Spawn (lines 219-222) and cancel (lines 457-461) symmetric with existing patterns." },
      { "check": "Pydantic constraints reasonable (gt=0.0, le=300.0)", "passed": true, "notes": "0.0 floor prevents a denial-of-service via tight loop; 300s ceiling keeps cadence operationally meaningful." },
      { "check": "Existing data-service tests pass (no fixture/test conflict with new field)", "passed": true, "notes": "tests/data/test_databento_data_service.py: 101/101 passed. grep confirms zero existing references to `_heartbeat_publish_task` or `_heartbeat_publish_loop` in that file." },
      { "check": "Full suite green", "passed": true, "notes": "5,238 passed in 66.84s with 32 pre-existing-category warnings." },
      { "check": "DEF-217 producer literal verified to match consumer policy table key", "passed": true, "notes": "Producer at databento_data_service.py:281 writes `alert_type=\"databento_dead_feed\"`; policy table at alert_auto_resolution.py:296-302 keys on `\"databento_dead_feed\"`. Test asserts the literal round-trips intact through the WS push." },
      { "check": "Suppression contract has falsifiable test assertion", "passed": true, "notes": "Captures pre-recovery heartbeat count and asserts no growth across a ~5-interval observation window with `_stale_published=True`." },
      { "check": "Heartbeat count assertion couples to predicate threshold", "passed": true, "notes": "Test asserts `len(heartbeats) >= 3`; predicate clears alert at `consecutive_healthy_heartbeats >= 3`." }
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Proceed to close-out at docs/sprints/sprint-31.91-reconciliation-drift/impromptu-b-closeout.md per Definition of Done.",
    "Sprint 31.91 may now proceed to Session 5c (the Impromptu A + B CLEAR gating condition is satisfied — Impromptu A landed CLEAR earlier, this impromptu CLEAR now)."
  ]
}
```

---

## Summary

Impromptu B delivers DEF-221 (DatabentoHeartbeatEvent producer wiring) and DEF-217 end-to-end validation cleanly. Three files modified (config + service + test); zero do-not-modify list violations. The producer reuses the existing `_running and not _stale_published` state combination per the prompt's scope boundary, the task lifecycle is symmetric with the three sibling tasks (`_stream_task`, `_stale_monitor_task`, `_heartbeat_task`), and the new E2E test genuinely drives the production emitter chain — the load-bearing `assert ws_msg["alert"]["alert_type"] == "databento_dead_feed"` is the regression guard the previous fabricated-event test was missing. Tests are green in isolation (1.45s) and against the full 5,238-test suite (66.84s).

## Strengths

- **Suppression contract is testable and tested.** `_stale_published` is the right reuse — it's already maintained by `_stale_data_monitor`, owned by exactly one writer, and flips on the right events (Stale → True, Resumed → False). The test pre-engages the flag BEFORE `start()`, confirms zero heartbeats during a 0.25s observation window (~5 intervals), then explicitly clears the flag to drive recovery. The captured-count diff is the falsifiable assertion.
- **Task lifecycle parallels the three sibling tasks.** Constructor initialization, spawn in `start()` step 8, cancel + suppress + await in `stop()`. Symmetric with `_heartbeat_task` cancellation immediately above. No orphan-task risk.
- **Producer/consumer string symmetry verified.** The production emitter at `argus/data/databento_data_service.py:281` publishes `alert_type="databento_dead_feed"`; the policy table at `argus/core/alert_auto_resolution.py:296-302` keys on the same literal. The test asserts the literal round-trips intact — DEF-217 has a real production-path regression guard now, not just the policy-exhaustiveness test from Impromptu A.
- **Heartbeat count assertion matches predicate threshold.** Predicate at `_databento_heartbeat_predicate:190` requires `consecutive_healthy_heartbeats >= 3`; test asserts `len(heartbeats) >= 3`. Coupled correctly.
- **Configurability respected.** `heartbeat_publish_interval_seconds` is a real `DatabentoConfig` field with `gt=0.0, le=300.0` constraints (production safe — won't accept 0 or negative or runaway values), default 30s production / 0.05s test. Test patches via constructor, not monkeypatch — clean.
- **Exception handling on publish.** `try/except Exception: logger.exception(...)` prevents a transient bus failure from killing the task — the loop recovers next interval.

## Concerns (LOW/INFO only)

### Concern 1 — LOW — Recovery transition tested without DataResumedEvent flow

The test sets `service._stale_published = False` directly, rather than driving a real Stale→Resumed flow via the `_stale_data_monitor`. This is acceptable for what the test is asserting (the producer's suppression-vs-publish branch + the consumer's 3-heartbeat clear), but it does mean the predicate's `DataResumedEvent` branch (`_databento_heartbeat_predicate:183-187`) is not exercised here. The existing `TestE2EDatabentoDeadFeed` and the unit-level predicate tests cover this elsewhere; not blocking.

**Remediation:** None required. Documented for future test-hygiene awareness.

### Concern 2 — LOW — Pre-existing `Task pending` warning surfaces in test teardown

Running the new test surfaces `Task was destroyed but it is pending! Task ... _log_post_start_symbology_size`. This is the `asyncio.ensure_future(self._log_post_start_symbology_size())` at `databento_data_service.py:392` (a 2-second post-start delayed log) — not tracked by `start()`/`stop()`, so it gets GC'd when the service is stopped early. Pre-existing in the production code; not introduced by this impromptu. Cosmetic.

**Remediation:** None for this impromptu. Could be tracked separately if Impromptu B's CLEAR is the trigger, but it's truly pre-existing.

### Concern 3 — INFO — Suppression test depends on subtle pre-start ordering

The test sets `service._stale_published = True` AFTER the `DatabentoDataService` constructor but BEFORE `start()`. This works because `_connect_live_session()` doesn't reset `_stale_published` (verified — only `_stale_data_monitor` writes to it). If a future change to `start()` or `_connect_live_session()` were to clear `_stale_published`, this test's suppression assertion would silently become a no-op (still pass but stop being load-bearing). Worth a comment in the test acknowledging this dependency, but it's noted in the lengthy production-side docstring already.

**Remediation:** None required. The production-side docstring documents the contract that protects the test.

## Scope Compliance

**PASS.** Diff touches exactly three files: `argus/core/config.py` (one Pydantic field added to `DatabentoConfig`), `argus/data/databento_data_service.py` (one task field, one task spawn, one task cancel, one new method), `tests/integration/test_alert_pipeline_e2e.py` (one new test class). Zero edits to `argus/data/alpaca_data_service.py`, `argus/execution/order_manager.py`, `argus/execution/ibkr_broker.py`, `argus/main.py`, `argus/core/events.py`, `argus/core/alert_auto_resolution.py`, or the migration framework. No new state attribute was introduced — the prompt's "no new state attr" boundary was respected.

## Test Compliance

**PASS.** New test passes in isolation (1.45s, well under the test's own ~2s budget). All 101 existing `tests/data/test_databento_data_service.py` tests still green. Combined E2E + data-service module run: 113 passed in 4.84s. Full suite: 5,238 passed in 66.84s. Test count grew by approximately 1 (the new E2E class with one test method) — matches the impl prompt's expectation.

## Documentation Compliance

**PASS for the implementation itself.** The new `_heartbeat_publish_loop` has a thorough docstring documenting the suppression contract, the `_stale_published` reuse rationale, and the cross-reference to the consumer predicate. The new config field has a description. The constructor field has a Sprint-31.91-Impromptu-B / DEF-221 attribution comment.

The close-out at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-b-closeout.md` and this review artifact satisfy the impl prompt's Definition of Done items.
