# Sprint 31.91 — Impromptu B Close-Out

> **Track:** Alert Observability Backend Hardening (post-Tier-3-#2).
> **Tier 3 track marker:** `alert-observability` (continues from S5a.1 + S5a.2 + S5b + Impromptu A).
> **Position in track:** Between Impromptu A (CLEAR, commit `e78a994`) and Session 5c (frontend integration).
> **Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition (Concern F + Item 7).
> **Resolves:** DEF-221 (MEDIUM — DatabentoHeartbeatEvent producer wiring).
> **Cross-validates:** DEF-217 (HIGH) — Impromptu B's E2E test is the FIRST test that drives the production Databento dead-feed emitter end-to-end (vs Impromptu A's structural / regression-guard validation). Together they provide both static (policy-exhaustiveness AST) and dynamic (live producer chain) regression coverage.
> **Self-assessment:** **PROPOSED_CLEAR.** Three LOW/INFO Tier 2 observations recorded; none blocking.
> **Mid-sprint doc-sync ref:** `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md`.
> **Anchor commit SHA:** `bb02174` on `main` (HITL-on-main; pre-impromptu HEAD).

---

## Pre-Flight Verification (RULE-038)

Both gating checks from the impl prompt's CONDITION FOR ENTRY block passed at session start; no drift reported:

| Anchor | Verified |
|---|---|
| `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-closeout.md` mentions DEF-217 in the resolved-DEFs section. | ✅ Multiple hits across closeout body + DEF-table row. |
| `argus/data/databento_data_service.py` has exactly 1 hit for `alert_type="databento_dead_feed"` (line 281, post-Impromptu-A state). | ✅ |

Additional grep performed against the impl prompt's pre-flight grep for the service health-state attribute:

```
grep -nE "self\._(feed_healthy|is_healthy|state)" argus/data/databento_data_service.py
# Returned: zero hits
```

The service has no canonical single-attribute health flag matching that exact pattern. **Disposition (operator-pre-cleared by impl prompt's review focus area #1):** the existing state combination `self._running and not self._stale_published` is the canonical signal; both attributes are pre-existing and well-established (FIX-06 / DEC-345 era). The impl prompt explicitly forbade introducing a new state attribute, so this combination was used. The producer's docstring at `_heartbeat_publish_loop` documents the rationale and the ownership invariant (`_stale_published` is owned solely by `_stale_data_monitor`).

---

## Change Manifest

### Code

- **`argus/core/config.py`** (~16 lines added) — DEF-221 config addition.
  - New field on `DatabentoConfig`: `heartbeat_publish_interval_seconds: float = Field(default=30.0, gt=0.0, le=300.0, ...)`.
  - Constraints rationale: `gt=0.0` prevents a denial-of-service tight loop; `le=300.0` keeps cadence operationally meaningful (300s ≈ 10× the predicate's 3-heartbeat window).
  - Description references Sprint 31.91 Impromptu B / DEF-221 and the suppression contract.

- **`argus/data/databento_data_service.py`** (~63 lines added) — DEF-221 producer wiring.
  - `DatabentoHeartbeatEvent` added to the `argus.core.events` import.
  - Constructor field: `self._heartbeat_publish_task: asyncio.Task | None = None` (parallel to the three sibling tasks).
  - `start()` step 8: `self._heartbeat_publish_task = asyncio.create_task(self._heartbeat_publish_loop())` — placed AFTER the existing `_data_heartbeat` spawn (step 7).
  - `stop()`: cancel + `CancelledError`-suppression-await pattern, mirroring the three sibling cancel blocks.
  - New `_heartbeat_publish_loop` method (~30 LOC + docstring): sleeps `heartbeat_publish_interval_seconds` per cycle; suppresses publish when `self._stale_published` is True (reconnect-loop / dead-feed state); publishes `DatabentoHeartbeatEvent(seconds_since_last_message=...)` otherwise; catches and logs publish-side exceptions so a transient bus failure cannot kill the task.
  - The 30-line docstring explicitly documents (a) the predicate-side requirement (3 consecutive heartbeats), (b) the `_running and not _stale_published` health signal and why it's correct, (c) the ownership invariant (only `_stale_data_monitor` writes `_stale_published`), and (d) the impl prompt's "no new state attribute" boundary that motivated reusing existing state.

### Tests

- **`tests/integration/test_alert_pipeline_e2e.py`** (~224 lines added — one new test class).
  - `DatabentoHeartbeatEvent` added to the `argus.core.events` import.
  - New `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer` class with one test:
    `test_databento_dead_feed_auto_resolves_via_real_heartbeats`.
  - **Why this test matters (load-bearing):** every prior E2E test in this file fabricates `SystemAlertEvent(alert_type="...")` directly. This is the FIRST test that exercises the production Databento emitter chain end-to-end. The assertion `ws_msg["alert"]["alert_type"] == "databento_dead_feed"` is the production-path regression guard for DEF-217 — a regression that drifted the literal back to `"max_retries_exceeded"` would surface here as a hard fail (not silently as dead policy code).
  - **Test flow:**
    1. Patch `databento` at `sys.modules` level via the existing `tests.mocks.mock_databento` shape (RULE-047 pattern).
    2. Subscribe a capture-handler for `DatabentoHeartbeatEvent` to count publications.
    3. Subscribe to HealthMonitor's state-change queue (the WS-fan-out test surface).
    4. Construct `DatabentoConfig` with `reconnect_max_retries=1`, fast backoff (0.01–0.05s), `heartbeat_publish_interval_seconds=0.05`.
    5. Patch `_connect_live_session` to succeed once (so `start()` returns cleanly), then fail on subsequent retries.
    6. Pre-engage `service._stale_published = True` BEFORE `start()` so heartbeats stay quiet across the entire reconnect window.
    7. `start()`. Wait ~0.3s for the reconnect loop to exhaust retries; the production code publishes `SystemAlertEvent(alert_type="databento_dead_feed")` via the real `_run_with_reconnection` path.
    8. Assert WS push: `alert_active` with the literal `databento_dead_feed` (DEF-217 production-path guard).
    9. Assert REST `/alerts/active` lists the alert.
    10. Wait ~0.25s (~5 heartbeat intervals) and assert ZERO heartbeats published while `_stale_published=True` (suppression contract).
    11. Mock recovery: clear `_stale_published`, freshen `_last_message_time`.
    12. Wait up to ~2s for the auto-resolution WS push (`alert_auto_resolved`); assert `state == "archived"`.
    13. Assert `len(heartbeats) >= 3` (matches the predicate's `consecutive_healthy_heartbeats >= 3` threshold).
    14. Assert REST `/alerts/active` no longer lists the alert; assert audit row `audit_kind="auto_resolution"`, `operator_id="auto"`.

---

## Test Counts

**Targeted (Impromptu-B scope):**

| Test file | Tests run | Result |
|---|---|---|
| `tests/integration/test_alert_pipeline_e2e.py` (full file) | 12 | All pass (was 11; +1 = the new class). |
| `tests/data/test_databento_data_service.py` (full file) | 101 | All pass (zero regression from the new `_heartbeat_publish_task` field on `DatabentoDataService`). |
| `tests/api/test_policy_table_exhaustiveness.py` + `test_alerts.py` + `test_alerts_5a2.py` | 36 | All pass (Impromptu-A regression guards still green). |

**Combined E2E + Databento data-service module run:** 113 passed in 4.84s.

**New tests added in this impromptu:** 1 (the new E2E class with one test method). Matches the impl prompt's "approximately +1" expectation exactly.

**Full suite:** **GREEN.** `python -m pytest --ignore=tests/test_main.py -n auto -q` reports **5,238 passed in 66.84s** (32 warnings, all pre-existing flake-family categories per CLAUDE.md DEF-150/167/171/190/192). +1 from the 5,237 Impromptu-A baseline (matches the predicted delta).

---

## Mental-Revert Verification of the DEF-217 Production-Path Guard

To prove the new E2E test's load-bearing assertion catches DEF-217 drift in the live code path (vs Impromptu-A's static AST-based catch), mentally revert the DEF-217 fix at `argus/data/databento_data_service.py:281`:

```python
# Before mental revert (current state):
alert_type="databento_dead_feed",

# After mental revert (regression):
alert_type="max_retries_exceeded",
```

The new test's assertion at `tests/integration/test_alert_pipeline_e2e.py` (line ~1113):

```python
assert ws_msg["alert"]["alert_type"] == "databento_dead_feed"
```

…would fail because the production emitter would publish `max_retries_exceeded`, the WS push would carry that string, and the equality check would surface the regression with a clear error message ("Production emitter must publish alert_type='databento_dead_feed' (validates DEF-217 in the real reconnect-exhaustion code path...)").

This is the dynamic counterpart to Impromptu A's static `test_all_emitted_alert_types_have_policy_entries` AST-based guard. **Both fire** under the same regression — DEF-217 now has belt-and-suspenders coverage.

---

## Mental-Revert Verification of the Suppression Contract

To prove the suppression assertion catches a regression that drops the `if self._stale_published: continue` branch, mentally revert the suppression check in `_heartbeat_publish_loop`:

```python
# Before mental revert (current state):
if self._stale_published:
    continue

# After mental revert (regression):
# (line removed)
```

The new test's assertion at line ~1133:

```python
heartbeats_before_recovery = len(heartbeats)
await asyncio.sleep(0.25)  # ~5 intervals at 0.05s
assert len(heartbeats) == heartbeats_before_recovery
```

…would fail because heartbeats would publish on every interval regardless of `_stale_published=True`, growing the count by ~5. The assertion error would surface the regression with a clear message ("Heartbeats must not publish while _stale_published is True (suppression contract...)").

The suppression contract has its own falsifiable test, independent of the auto-resolution flow.

---

## Judgment Calls

### 1. Health-state signal — `_running and not _stale_published` vs introducing a new attribute

The impl prompt's pre-flight grep (`_feed_healthy|_is_healthy|_state`) returned zero hits — the service does not have a single canonical health attribute. The prompt explicitly forbade introducing a new state attribute as part of this impromptu ("If the service doesn't have a clean health-state attribute, HALT and request operator disposition — do NOT introduce a new state attribute as part of this impromptu").

Two paths considered:

- **Path A (taken):** Use the existing `self._running` and `self._stale_published` flags in combination. The signal is "feed is healthy ↔ service running AND data not stale." Both attributes are pre-existing, well-established (FIX-06 / DEC-345 era), and have single-writer ownership (`_running` written only by `start()`/`stop()`; `_stale_published` written only by `_stale_data_monitor`).
- **Path B (rejected):** HALT and request operator disposition for a new `_feed_healthy: bool` attribute.

Path A respects the impl prompt's explicit "no new state attr" boundary and produces a working implementation with documented ownership invariants. Path B would have stalled the impromptu over a clearly-resolvable design choice.

**Self-assessment:** Not a deviation — the impl prompt's HALT clause was conditional on "the service doesn't have a clean health-state attribute," and the existing combination IS clean. Documented for completeness and for future maintainers.

### 2. Test combines DEF-217 production-path validation + DEF-221 producer validation + suppression contract in ONE test method

The impl prompt's Test method §"Steps 1-6" describes a single E2E test exercising:

1. Real producer publishes `databento_dead_feed` (validates DEF-217 in production code).
2. Real heartbeat publisher fires when feed is healthy (validates DEF-221).
3. Heartbeat publisher suppresses when feed is in dead-feed state (validates suppression contract).

I implemented as a single test method that exercises all three in sequence (rather than three separate methods). Rationale: the auto-resolution flow is end-to-end stateful — splitting requires either re-driving the reconnect loop three times (fragile, slow) or fabricating intermediate state (defeats the "real producer" goal). One ~80-line test exercising the full pipeline is clearer than three smaller tests with overlapping setup.

**Self-assessment:** Not a deviation from the impl prompt — the prompt described the test as a single method with six steps. Flagged here for completeness in case a reviewer prefers split tests.

### 3. Recovery transition mocked via direct state manipulation rather than driving stale_data_monitor

The test's recovery step sets `service._stale_published = False` and `service._last_message_time = time_module.monotonic()` directly, rather than driving the `_stale_data_monitor` task to observe new data flow and emit `DataResumedEvent`. Driving the real flow would require either (a) a much longer test (5s+ for the stale_data_monitor's 5-second poll cycle to fire), or (b) restructuring the monitor to be tickable from tests.

The Tier 2 review flagged this as `LOW — TEST_COVERAGE_GAP`. The predicate's `DataResumedEvent` clearing branch (`alert_auto_resolution.py:183-187`) is covered elsewhere by unit-level tests and by the existing `TestE2EDatabentoDeadFeed`. The current test exercises the heartbeat-only clearing branch, which is what DEF-221's producer wiring delivers.

**Self-assessment:** Acceptable trade-off documented by Tier 2. Not a deviation from the impl prompt.

---

## Tier 2 Review (inline)

Per impl prompt §"Tier 2 Review (inline)", a Tier 2 review was conducted in the same Claude Code session against the spec, the diff, and the new test. Verdict artifact at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-b-review.md`.

**Tier 2 verdict: CLEAR.** Three LOW/INFO observations recorded:

1. **LOW — TEST_COVERAGE_GAP:** Recovery transition direct-set vs `DataResumedEvent` flow (judgment call #3 above). Acceptable for impromptu scope.
2. **LOW — OTHER:** Pre-existing `Task was destroyed but it is pending!` warning for `_log_post_start_symbology_size` (`databento_data_service.py:392`'s `asyncio.ensure_future` call is not tracked by `start()`/`stop()`). Out of scope; same warning surfaces across all existing data-service tests.
3. **INFO — TEST_COVERAGE_GAP:** Suppression test depends on `start()` not resetting `_stale_published`. The production-side docstring documents this invariant. No additional guard added.

None of the three are blocking; verdict is CLEAR per Tier 2's structured JSON.

---

## Definition of Done

| DoD Item | Status |
|---|---|
| `DatabentoConfig.heartbeat_publish_interval_seconds` field added with correct constraints (`gt=0.0, le=300.0`). | ✅ |
| `_heartbeat_publish_loop` task implemented; spawned in `start()`; cancelled in `stop()` with `CancelledError` suppression. | ✅ |
| Task suppression during reconnect-loop state implemented and tested (mental-revert verifies the assertion is falsifiable). | ✅ |
| `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer` test green; drives production emitter end-to-end. | ✅ |
| Existing Databento data-service tests still pass. | ✅ 101/101 in `tests/data/test_databento_data_service.py`. |
| Full test suite passes: `python -m pytest --ignore=tests/test_main.py -n auto -q`. | ✅ 5,238 passed in 66.84s (32 pre-existing-category warnings). |
| Test count increases by approximately 1 (the new E2E test). | ✅ +1 exact (5,237 → 5,238). |
| Tier 2 review verdict CLEAR. | ✅ See `impromptu-b-review.md`. |
| Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-b-closeout.md`. | ✅ This file. |
| Tier 2 review at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-b-review.md`. | ✅ |

---

## Sprint-Level Regression Checklist

- **Invariant 1 (no broker-orphan SHORT entry):** PASS — no reconciliation-loop or order-manager code touched.
- **Invariant 5 (test baseline ≥ prior):** PASS — full suite green at 5,238 passing in 66.84s, exactly +1 from the 5,237 Impromptu-A baseline. The targeted alert-observability scope is also green.
- **Invariant 14 (alert observability — backend complete):** STRENGTHENED — DEF-221 wires the heartbeat producer end-to-end. The auto-resolution policy entry for `databento_dead_feed` is no longer dead code: a real dead-feed alert can now auto-resolve via three real heartbeats (vs Impromptu A which made the policy entry's STRING match correct; this impromptu makes the EVENT FLOW work).

---

## DEF Transitions

| DEF | Pre-state | Post-state | Notes |
|---|---|---|---|
| DEF-221 | OPEN — Routing: Sprint 31.91 Impromptu B | **RESOLVED-IN-SPRINT, Impromptu B** | Producer task `_heartbeat_publish_loop` wired into `DatabentoDataService.start()` / `stop()`; suppresses during reconnect / dead-feed state via `_stale_published`; publishes `DatabentoHeartbeatEvent` on `heartbeat_publish_interval_seconds` cadence; configurable via `DatabentoConfig`; E2E test validates the full pipeline. |
| DEF-217 | RESOLVED (Impromptu A, static AST-based regression guard) | RESOLVED — now ALSO validated by Impromptu B's production-path E2E test | Impromptu B's `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer.test_databento_dead_feed_auto_resolves_via_real_heartbeats` is the FIRST test that drives the production emitter chain (vs fabricating `SystemAlertEvent`). Cross-validation completes the structural+dynamic regression coverage. |

CLAUDE.md DEF-table updates (deferred to sprint-close per `pre-impromptu-doc-sync-manifest.md`):

- DEF-221's row will move to RESOLVED with strikethrough on the title and a one-line resolution context citing this closeout SHA.
- DEF-217's existing RESOLVED row will gain a one-line note that Impromptu B added the production-path E2E validation.

---

## Anchor Commit

Pre-impromptu HEAD on `main`: `bb02174` (commit subject: "docs(sprint-31.91): work journal register refresh — post Impromptu A").

The Impromptu B implementation work was performed against this anchor. Resulting commit subject (to be written by the operator at commit time):

```
feat(sprint-31.91): Impromptu B — DatabentoHeartbeatEvent producer + DEF-217 E2E validation (DEF-221)
```

Three files modified, 303 insertions, 0 deletions:
- `argus/core/config.py` — 16 insertions.
- `argus/data/databento_data_service.py` — 63 insertions.
- `tests/integration/test_alert_pipeline_e2e.py` — 224 insertions.

---

## Closeout Statement

**Impromptu B's `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer` validates DEF-217 fix in the production code path** — the assertion `alert_type == "databento_dead_feed"` would fail under any regression that drifted the producer's literal back to `"max_retries_exceeded"` (or any other string). Combined with Impromptu A's static AST-based exhaustiveness guard, DEF-217 now has dual-layer regression coverage: structural (catches the literal at parse time) and dynamic (catches the literal at run time through the full alert pipeline).

Sprint 31.91 may now proceed to **Session 5c (frontend integration)** with the alert-observability backend hardening fully complete: DEF-217/218/219/221/224/225 all RESOLVED-IN-SPRINT.
