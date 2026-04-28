# Sprint 31.91 — Impromptu B Implementation Prompt: Databento Heartbeat Producer

> **Workflow contract:** authored under `templates/implementation-prompt.md` v1.5.0 (structural anchors); references `protocols/mid-sprint-doc-sync.md` v1.0.0 for closeout discipline.
> **Sprint:** 31.91 reconciliation-drift.
> **Position in track:** between Impromptu A and Session 5c.
> **Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition.
> **Resolves:** DEF-221 (MEDIUM) + validates DEF-217 fix end-to-end.
> **Sprint-spec deliverable:** D15.
> **Tier 2 review:** inline within this implementing session.

## CONDITION FOR ENTRY

**Impromptu A must have landed CLEAR.** This impromptu's end-to-end validation test depends on DEF-217's fix (the production Databento emitter publishing `databento_dead_feed`, not `max_retries_exceeded`). If Impromptu A has not landed CLEAR per its Tier 2 review, HALT.

Pre-flight verification:
```bash
grep "DEF-217" docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-closeout.md
# Expected: hits in resolved-DEFs section

grep 'alert_type="databento_dead_feed"' argus/data/databento_data_service.py
# Expected: 1 hit (the post-Impromptu-A state)
```

If either check fails, HALT and route back to Impromptu A.

## Pre-Flight

Read the following inputs in full:
- This impl prompt.
- `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended; Concern F + Item 7).
- `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` (D15 deliverable + AC).
- `argus/data/databento_data_service.py` (in full — both the dead-feed reconnect loop AND the new heartbeat task site).
- `argus/core/events.py` (`DatabentoHeartbeatEvent` definition).
- `argus/core/alert_auto_resolution.py` (`_databento_heartbeat_predicate`).
- `tests/integration/test_alert_pipeline_e2e.py` (existing E2E patterns; the new test class lives here).
- `tests/data/test_databento_data_service.py` (existing data-service tests).

## Scope

Two items: producer wiring + end-to-end validation test.

### Requirement 1 — DEF-221: Add heartbeat-publishing task

**Config addition.** In `argus/core/config.py`, find the `DatabentoConfig` Pydantic model (anchor: `class DatabentoConfig`). Add a new field:

```python
heartbeat_publish_interval_seconds: float = Field(
    default=30.0,
    gt=0.0,
    le=300.0,
    description=(
        "Interval at which DatabentoDataService publishes "
        "DatabentoHeartbeatEvent when the feed is healthy. "
        "Suppressed during reconnect loop. "
        "Sprint 31.91 Impromptu B (DEF-221)."
    ),
)
```

**Producer wiring.** In `argus/data/databento_data_service.py`:

1. Add a private async method `_heartbeat_publish_loop` that runs while the feed is in HEALTHY state and publishes `DatabentoHeartbeatEvent(provider="databento")` every `heartbeat_publish_interval_seconds`. Suppressed during reconnect-loop state.

2. Spawn the task in the service's `start()` method (`asyncio.create_task(self._heartbeat_publish_loop())`); cancel in `stop()` with `CancelledError` suppression.

3. The task must check feed health via the service's existing health-state attribute (find by grep: `grep -n "_feed_healthy\|_is_healthy\|_state" argus/data/databento_data_service.py`); only publish when healthy.

**Pre-flight grep-verify for service health attribute:**
```bash
grep -nE "self\._(feed_healthy|is_healthy|state)" argus/data/databento_data_service.py
# Expected: 2-5 hits identifying the canonical health state attribute
```

If the service doesn't have a clean health-state attribute, HALT and request operator disposition — do NOT introduce a new state attribute as part of this impromptu.

### Requirement 2 — End-to-end validation test

**Anchor:** in `tests/integration/test_alert_pipeline_e2e.py`, after the existing `TestE2EDatabentoDeadFeed` class (or wherever Impromptu A's `TestE2EIBKRAuthFailureAutoResolution` was added — append at the end either way).

**New test class:** `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer`.

**Test method:** `test_databento_dead_feed_auto_resolves_via_real_heartbeats`. Steps:
1. Start `DatabentoDataService` with mocked Databento client that initially fails to connect (drives reconnect loop).
2. Drive the loop to retries-exhausted; verify production emitter publishes `SystemAlertEvent(alert_type="databento_dead_feed")` (NOT a fabricated event — this is the load-bearing assertion that DEF-217 was actually fixed).
3. Verify alert is ACTIVE via REST `/alerts/active`.
4. Mock recovery (Databento client now connects successfully); verify `_feed_healthy` flips to True.
5. Wait for ≥3 heartbeat intervals; verify `DatabentoHeartbeatEvent` published 3+ times.
6. Verify alert auto-resolves (WS push `alert_auto_resolved`; REST `/alerts/active` no longer lists; audit row `audit_kind="auto_resolution"`).

**Why this test matters:** every existing E2E test in this file fabricates `SystemAlertEvent(alert_type="...")` directly. This is the FIRST test that exercises the production Databento emitter chain end-to-end. It validates that DEF-217 + DEF-221 together produce a working auto-resolution pipeline.

## Scope Boundaries (do-not-modify)

- `argus/data/alpaca_data_service.py` — zero edits.
- `argus/execution/order_manager.py`, `argus/execution/ibkr_broker.py` — zero edits.
- `argus/main.py` — zero edits (the new task is owned by `DatabentoDataService.start()`, no main.py wiring needed).
- `argus/core/events.py` — `DatabentoHeartbeatEvent` already exists (S5a.2); zero edits.
- `argus/core/alert_auto_resolution.py` — `_databento_heartbeat_predicate` already exists; zero edits.
- The migration framework — zero edits (no schema changes).

## Tier 2 Review (inline)

After implementation, spawn a Tier 2 review subagent within this same Claude Code session.

Review focus areas:
1. The heartbeat task properly suppresses during reconnect-loop state (verify via test that drives the dead-feed state and confirms zero heartbeat publications during the reconnect window).
2. Task is properly cancelled in `stop()` — no orphan task leakage on service stop.
3. The end-to-end test is genuinely end-to-end (drives production code, NOT fabricated events).
4. Heartbeat interval is configurable (test patches the config to a small value for fast test execution).
5. No regression in existing Databento data-service tests.

Verdict format: structured JSON per `schemas/structured-review-verdict-schema.md`.

## Definition of Done

- [ ] `DatabentoConfig.heartbeat_publish_interval_seconds` field added with correct constraints.
- [ ] `_heartbeat_publish_loop` task implemented; spawned in `start()`; cancelled in `stop()`.
- [ ] Task suppression during reconnect-loop state implemented and tested.
- [ ] `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer` test green; drives production emitter end-to-end.
- [ ] Existing Databento data-service tests still pass.
- [ ] Full test suite passes: `python -m pytest --ignore=tests/test_main.py -n auto -q`.
- [ ] Test count increases by approximately 1 (the new E2E test).
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-b-closeout.md`.
- [ ] Tier 2 review at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-b-review.md`.

## Closeout requirements

Per `protocols/mid-sprint-doc-sync.md` v1.0.0 + the manifest pattern:
- `mid_sprint_doc_sync_ref: "docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md"`.
- DEF transitions claimed: DEF-221 → "RESOLVED-IN-SPRINT, Impromptu B".
- DEF cross-validation: DEF-217 end-to-end validation now confirmed (close-out should explicitly state "Impromptu B's TestE2EDatabentoDeadFeedAutoResolveWithRealProducer validates DEF-217 fix in production code path").
- Anchor commit SHA.
- Tier 3 track marker: `alert-observability`.
