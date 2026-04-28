# Sprint 31.91 — Session 5b Close-Out

> **Track:** Alert Observability Backend (Session 5a.1 → 5a.2 → **5b**).
> **Position in track:** Third and final backend session.
> **Self-assessment:** **PROPOSED_CLEAR** (one MINOR_DEVIATION flagged below — refined behavioral Alpaca check, see §"Judgment Calls").

---

## Tier 3 #2 invocation pre-amble

**Sessions 5a.1 + 5a.2 + 5b are now on `main` (5b commit pending the Tier 2 review).**

**Operator action required:** invoke **Tier 3 architectural review #2** on the
combined 5a.1 + 5a.2 + 5b diff BEFORE proceeding to Session 5c. This is a phase
boundary per `escalation-criteria.md` §A1.5; the alert-observability backend is
sealed by Tier 3 #2, not by any individual Tier 2 verdict.

The combined-diff scope:

```
git diff 5f6b2a6..HEAD -- argus/api/routes/alerts.py \
  argus/api/websocket/alerts_ws.py argus/api/server.py argus/api/routes/__init__.py \
  argus/api/websocket/__init__.py argus/core/alert_auto_resolution.py \
  argus/core/config.py argus/core/events.py argus/core/health.py \
  argus/data/databento_data_service.py argus/data/migrations/ \
  argus/execution/ibkr_broker.py argus/execution/order_manager.py argus/main.py \
  tests/api/test_alerts.py tests/api/test_alerts_5a2.py tests/core/test_events.py \
  tests/execution/order_manager/test_def214_eod_verify.py \
  tests/integration/test_alert_pipeline_e2e.py
```

---

## Change Manifest

### Code

- **`argus/execution/ibkr_broker.py`** (95 insertions, 3 deletions)
  1. Added `SystemAlertEvent` to the `argus.core.events` import block.
  2. Updated `_reconnect()` docstring to document the new emit-on-exhaustion behavior.
  3. **Resolved DEF-014 emitter at `_reconnect`** — replaced the single-line
     `# TODO: Publish SystemAlertEvent when available (DEF-014)` with a
     full `SystemAlertEvent(alert_type="ibkr_disconnect", severity="critical")`
     publish wrapped in try/except so a publish failure cannot propagate
     out of the reconnection loop.
  4. **Resolved DEF-014 emitter at `_on_error` CRITICAL branch** — added
     an `else` branch on the `is_connection_error` guard that emits
     `SystemAlertEvent(alert_type="ibkr_auth_failure", severity="critical")`
     for any CRITICAL non-connection IBKR error (e.g., 203 "security not
     available for this account", 321 "Server error validating API client
     request"). Wired through a new private helper
     `_emit_ibkr_auth_failure_alert(error_code, error_string, contract)`
     that bridges the synchronous `_on_error` callback to the asyncio
     event bus via `asyncio.ensure_future`.

### Tests

- **`tests/integration/test_alert_pipeline_e2e.py`** (NEW — 10 tests across 6 test classes)
  - `TestIBKRDisconnectEmitter` (Tests 1, +1 defensive)
    - `test_ibkr_disconnect_reconnect_failure_emits_system_alert` — mocks
      `ib_async` to always raise on `connectAsync`, drives `_reconnect` to
      exhaustion, asserts exactly one `SystemAlertEvent(alert_type="ibkr_disconnect")`
      published with full metadata.
    - `test_ibkr_disconnect_emit_does_not_raise_on_publish_failure` —
      defensive: a subscriber that raises on publish must not propagate
      out of `_reconnect` (verifies the try/except wrapper).
  - `TestIBKRAuthFailureEmitter` (Tests 2, +1 boundary check)
    - `test_ibkr_auth_permission_failure_emits_system_alert` — fires
      `_on_error(error_code=203, ...)`, asserts exactly one
      `SystemAlertEvent(alert_type="ibkr_auth_failure")` published with
      `metadata={error_code, error_message, symbol, client_id, detection_source}`.
    - `test_ibkr_connection_critical_does_not_emit_auth_alert` — fires
      `_on_error(error_code=502, ...)` (a CRITICAL connection error) and
      asserts NO `ibkr_auth_failure` is emitted (the existing reconnection
      path owns recovery for those).
  - `TestE2EDatabentoDeadFeed` (Test 3) — emit `databento_dead_feed`
    via Event Bus → assert WS push (`alert_active`) via
    `subscribe_state_changes` queue → assert REST `/active` returns it →
    POST `/{alert_id}/acknowledge` returns 200 with `state="acknowledged"` →
    assert WS push (`alert_acknowledged`) → assert audit-log row with
    `audit_kind="ack"` in `alert_acknowledgment_audit`.
  - `TestE2EIBKRDisconnectAutoResolution` (Test 4) — emit `ibkr_disconnect`
    → consume → REST → fire `IBKRReconnectedEvent` → assert WS push
    (`alert_auto_resolved`) → assert REST `/active` no longer lists it →
    assert audit row with `audit_kind="auto_resolution"`, `operator_id="auto"`.
  - `TestE2EPhantomShortAutoResolution` (Test 5) — reads
    `health_monitor._reconciliation_config.broker_orphan_consecutive_clear_threshold`
    at runtime (NOT hardcoded `5`); emits `phantom_short` for AAPL; fires
    exactly `threshold` `ReconciliationCompletedEvent`s with AAPL=0; asserts
    auto-resolution + WS + REST `/history` + audit row.
  - `TestE2EAcknowledgmentPersistsRestart` (Test 6) — emit + ack via
    REST; build a fresh `HealthMonitor` against the same `operations.db`;
    call `rehydrate_alerts_from_db()`; assert acknowledged state survives
    AND audit row queryable directly.
  - `TestE2EPhantomShortRetryBlockedNeverAutoResolves` (Test 7) — emit
    `phantom_short_retry_blocked`; fire **100** `ReconciliationCompletedEvent`s
    (intentionally large to prove "across many cycles, no resolution");
    assert alert STAYS `active`; ack via REST; assert state="acknowledged".
    Pins the policy-table NEVER row for the alert type Session 3 introduced.
  - `TestAlpacaBoundary` (Test 8 — behavioral Alpaca anti-regression) —
    `inspect.getsource(argus.data.alpaca_data_service)`; tokenize via
    `tokenize.generate_tokens`; reject COMMENT + STRING tokens; assert
    `"SystemAlertEvent" not in <executable_src>`. See "Judgment Calls"
    below for why the prompt's literal substring check was refined.

### Mock fixture additions

- New self-contained fixtures in the test file (rather than extending
  `tests/api/conftest.py`):
  - `operations_db` — fresh `operations.db` per test.
  - `system_config` — SystemConfig with `data_dir` pointing at the temp DB
    parent (so the alerts route's `_resolve_operations_db_path` lands on
    the test's temp DB).
  - `event_bus`, `health_monitor`, `app_state`, `client`, `auth_headers`,
    `jwt_secret` — full E2E rig with the HealthMonitor's `operations_db_path`
    wired (the shared `tests/api/conftest.py::test_health_monitor` does NOT
    pass `operations_db_path`, so audit rows would not be persisted).
  - `mock_ib_for_emitter`, `ibkr_config_for_emitter` — minimal IBKR mocks
    for the broker-emitter unit tests.

The shared `tests/api/conftest.py` was deliberately NOT modified — the
prompt's "Mock updates (~2)" hint was satisfied by adding fixtures local
to the new test file rather than risking a regression in 25+ unrelated
tests that depend on `test_health_monitor`'s in-memory-only mode. See
"Judgment Calls" for full reasoning.

### Files that the do-not-modify list flagged

- **`argus/data/alpaca_data_service.py`** — confirmed ZERO edits via
  `git diff --stat argus/data/alpaca_data_service.py` (empty output).
- **`argus/execution/order_manager.py`** lines `:1670-1750` (IMPROMPTU-04
  fix) — confirmed ZERO edits to that range; this session does not
  touch `order_manager.py` at all (verified by `git diff --stat`:
  the only modified file is `argus/execution/ibkr_broker.py`).

---

## Judgment Calls

### 1. Stale line-number references in the prompt (RULE-038)

The prompt referenced `argus/execution/ibkr_broker.py:453` and `:531` as
the IBKR emitter TODO sites. Pre-flight grep showed those line numbers
are **stale** — they predate intervening commits. Current state:

- `:453` referenced in prompt → actual TODO is at **`:570`** (the `_reconnect`
  failure path, after retries exhausted; the docstring at `:492` references
  the same `DEF-014` deferral).
- `:531` referenced in prompt → there is no separate TODO at this line
  number. The "auth/permission failure" path the prompt describes is the
  CRITICAL non-connection branch in `_on_error` (around `:416-420`),
  which previously had no emitter at all (just `pass` after the `is_connection_error`
  check).

Per RULE-038, I treated the prompt's line numbers as directional and
worked from the semantic intent ("emit on disconnect/reconnect failure"
and "emit on auth/permission failure"). Both emitters were wired at the
correct semantic sites:

- Disconnect/reconnect failure → at the bottom of `_reconnect()` after
  the "All retries exhausted" CRITICAL log.
- Auth/permission failure → in the new `else` branch on
  `is_connection_error` inside `_on_error`'s CRITICAL handler. Routes
  to a new `_emit_ibkr_auth_failure_alert(error_code, error_string, contract)`
  helper for testability.

This finding is **flagged here** rather than left silent per RULE-038.

### 2. Refined behavioral Alpaca anti-regression check

The prompt's Test 8 specified literally:

```python
src = inspect.getsource(mod)
assert "SystemAlertEvent" not in src, (...)
```

Run as-written, this **fails** against the current state of
`argus/data/alpaca_data_service.py:598`:

```python
# TODO: Publish SystemAlertEvent when implemented in Sprint 5
```

The string `"SystemAlertEvent"` is in the existing TODO comment. The DoD
explicitly forbids modifying `alpaca_data_service.py`. So the literal
test is **mutually exclusive with** the do-not-modify constraint.

I refined the test to tokenize the source and reject COMMENT + STRING
tokens before the substring search. This:

- **Preserves the architectural intent** the prompt called out
  ("enforces the architectural constraint at semantic level"). The
  semantic constraint is "Alpaca shall not emit `SystemAlertEvent`".
  Comments don't emit anything; `import SystemAlertEvent` or
  `SystemAlertEvent(...)` would still appear as `NAME` tokens and trip
  the assertion.
- **Honors the do-not-modify boundary** on `alpaca_data_service.py`.
- **Stays robust to refactors** — exactly the property the prompt
  emphasized over the prior brittle line-number check.
- **Keeps the failure message** pointing at DEF-178/183, Sprint 31.94
  retirement (per the prompt's "future maintainer" hint).

The test docstring documents this judgment call so a Tier 2 / Tier 3
reviewer can see the decision and the rationale without having to
reconstruct it.

**Self-assessment:** This is a **MINOR_DEVIATION** from the literal
spec text — the assertion body changed from `"SystemAlertEvent" not in src`
to `"SystemAlertEvent" not in <comment-and-string-stripped src>`. The
deviation is mechanical (one extra preprocessing step), the architectural
constraint is intact, and the alternative (modify `alpaca_data_service.py`
to delete the comment) would have violated a higher-priority constraint.

### 3. Conftest mock updates — kept local rather than shared

The prompt mentioned `Mock updates (~2)` to `tests/api/conftest.py`. I
chose instead to add the E2E-specific fixtures (HealthMonitor with
`operations_db_path` wired, plus IBKR mocks for the emitter unit tests)
**locally** in `tests/integration/test_alert_pipeline_e2e.py` rather
than shared via `tests/api/conftest.py`. Reasons:

- The shared `test_health_monitor` fixture is consumed by ~25 unrelated
  tests that test the in-memory-only state machine (no operations.db
  persistence). Changing its signature would either (a) require
  updating every consumer, expanding scope, or (b) introduce
  conditional behavior that hides real bugs.
- The `mock_ib_for_emitter` + `ibkr_config_for_emitter` fixtures
  duplicate ~50 lines of fixture code from `tests/execution/test_ibkr_broker.py`,
  but consolidating would require refactoring fixture ownership across
  two test trees — out of session scope per RULE-007.

The duplication is intentional and contained to the new E2E file.

---

## Scope Verification

### Definition of Done — gate-by-gate (RULE-005)

| DoD Item | Status | Evidence |
|---|---|---|
| `:453` emitter resolved with full alert metadata payload | ✅ | `argus/execution/ibkr_broker.py` `_reconnect()` end — emits `SystemAlertEvent(alert_type="ibkr_disconnect")` with metadata `{max_retries, client_id, host, port, detection_source}`. Stale line — actual site is `:570` (RULE-038 disclosure). |
| `:531` emitter resolved with full alert metadata payload | ✅ | `argus/execution/ibkr_broker.py` `_on_error()` CRITICAL non-connection branch — emits via `_emit_ibkr_auth_failure_alert()` with metadata `{error_code, error_message, symbol, client_id, detection_source}`. Stale line — actual site is the `else` branch around `:416-420` (RULE-038 disclosure). |
| `argus/data/alpaca_data_service.py` ZERO edits | ✅ | `git diff --stat argus/data/alpaca_data_service.py` returns empty. |
| 8 E2E + emitter tests + 2 mock updates added; all green | ✅ | 10 new tests added (8 prompt tests + 2 defensive sub-tests). All green. Mock updates kept local to the new test file (see Judgment Call 3). |
| Behavioral anti-regression test pins Alpaca abstinence semantically | ✅ | `TestAlpacaBoundary::test_alpaca_data_service_does_not_emit_system_alert_events` uses `tokenize` to strip COMMENT+STRING tokens, then asserts. See Judgment Call 2 for the literal-vs-semantic refinement. |
| Test 5 specifically pins the 5-cycle threshold = 2c.2's `broker_orphan_consecutive_clear_threshold` | ✅ | Test reads `health_monitor._reconciliation_config.broker_orphan_consecutive_clear_threshold` at runtime AND fires exactly that many cycles. Hardcoding `5` would have hidden a future config drift. |
| Test 7 specifically pins the NEVER row for `phantom_short_retry_blocked` | ✅ | `TestE2EPhantomShortRetryBlockedNeverAutoResolves` fires 100 events, asserts state stays `active`, then ack via REST clears it. The 100-cycle count is unmistakably not a `range(1)` typo. |
| CI green; pytest baseline ≥ Session 5a.2 + 8 | ✅ | Baseline was 5,222. After session: **5,232 passing** (+10 = 8 prompt tests + 2 defensive sub-tests). +0 new warnings to the IBKR-broker test category beyond pre-existing AsyncMock coroutine warnings (4 new from new IBKR-emitter tests, all matching the existing pattern). |
| Tier 2 review verdict CLEAR | 🔜 | Review prompt invoked below; verdict pending. |
| Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-5b-closeout.md` | ✅ | This file. |
| Tier 3 architectural review #2 invoked on combined 5a.1+5a.2+5b diff | 🔜 | Operator-triggered post-merge per `escalation-criteria.md` §A1.5. See pre-amble at top. |

### Files modified (`git diff --stat` summary)

```
 argus/execution/ibkr_broker.py | 98 ++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 95 insertions(+), 3 deletions(-)
```

### Files added

```
 tests/integration/test_alert_pipeline_e2e.py  (NEW, 10 tests)
```

### Files explicitly NOT modified (do-not-modify list)

- `argus/data/alpaca_data_service.py` — verified zero edits.
- `argus/execution/order_manager.py` — verified zero edits to `:1670-1750`
  (whole file unmodified this session).

---

## Pipeline Coverage Matrix

Each emitter type × each pipeline stage. Tests 3-7 plus the two emitter
unit tests cover the matrix. Cell text identifies the test that exercises
that cell.

| Emitter | REST `/active` | WS push (`alert_active`) | Acknowledgment via REST | Audit-log row | Auto-resolution |
|---|---|---|---|---|---|
| `databento_dead_feed` | Test 3 | Test 3 | Test 3 (ack flow) | Test 3 (`audit_kind=ack`) | Covered by `tests/api/test_alerts_5a2.py::test_databento_dead_feed_3_healthy_heartbeats` (5a.2) |
| `ibkr_disconnect` | Test 4 | Test 4 | (operator-ack-optional; not exercised — auto-res path tested instead) | Test 4 (`audit_kind=auto_resolution`) | Test 4 (via `IBKRReconnectedEvent`) |
| `ibkr_auth_failure` | Emitter unit Test 2 (publish verified) | Same chain — covered by 5a.2 fan-out tests | Same | Same | Predicate covered in `argus/core/alert_auto_resolution.py::_ibkr_auth_success_predicate`; auto-res path covered structurally by Test 4 (same predicate-chain shape, different consumed event types) |
| `phantom_short` | Test 5 | Test 5 | (operator-ack-optional; auto-res path tested) | Test 5 (`audit_kind=auto_resolution`) | Test 5 (via N `ReconciliationCompletedEvent`s) |
| `phantom_short_retry_blocked` | Test 7 (covered via REST ack path) | Snapshot covered by 5a.2 fan-out tests | Test 7 (REST ack flow) | Test 7 (`audit_kind=ack`) | NEVER (Test 7 — 100 events, no resolution) |
| `phantom_short` (persistence-survives-restart) | Test 6 (REST ack flow) | (out of scope) | Test 6 | Test 6 (audit row queryable post-restart) | (out of scope) |

Gap analysis:

- `ibkr_auth_failure` does NOT get its own dedicated end-to-end auto-resolution
  test; the auto-resolution predicate is exercised in `tests/api/test_alerts_5a2.py`
  via the policy table's exhaustiveness test (Test #11 there) and via the
  same-shape ibkr_disconnect E2E test (Test 4 here, which uses the same
  `IBKRReconnectedEvent`-clears-the-alert chain). This is acceptable —
  `ibkr_auth_failure`'s predicate is the same shape as `ibkr_disconnect`'s,
  with `OrderFilledEvent` added as an additional clearing event. A
  dedicated E2E for auth-failure → OrderFilledEvent → auto-resolve would
  add coverage but no new structural verification beyond Test 4. Flagged
  here for Tier 3 #2 to validate the gap closure.
- `cancel_propagation_timeout` (Session 1c emitter) is policy-table NEVER;
  its NEVER behavior is covered by `tests/api/test_alerts_5a2.py::test_cancel_propagation_timeout_never_auto_resolves`.
  Test 7 here covers the operator-ack path on a NEVER alert generically;
  cancel_propagation_timeout's specific E2E is implicitly covered by
  the same shape.
- `stranded_broker_long` (Session 2b.1 emitter) is functionally identical
  to `phantom_short` for predicate purposes; covered by 5a.2 tests.
- `phantom_short_startup_engaged` (Session 2d emitter) auto-resolution is
  predicate-tested in `tests/api/test_alerts_5a2.py`. The 24h-elapsed
  branch isn't end-to-end here (would require time-mocking inside the
  predicate). Tracked as a recommended future test, not a Sprint 31.91
  gate item.

---

## Alpaca Abstinence Rationale (MEDIUM #13 restatement for posterity)

`argus/data/alpaca_data_service.py:598` carries a TODO comment for a
future SystemAlertEvent emitter. Per MEDIUM #13, the file is queued for
**retirement by deletion** in Sprint 31.94 (DEF-178 retires the
dependency; DEF-183 retires the file itself). Wiring the emitter just
to delete it 2 sprints later would be wasted work AND introduce an
operator-confusion risk window where Alpaca emits production-shape
`SystemAlertEvent`s that the operator might mistake for actionable
production signal (when in fact ARGUS doesn't trade on Alpaca anymore).

The behavioral test (`TestAlpacaBoundary::test_alpaca_data_service_does_not_emit_system_alert_events`)
enforces this constraint at the architectural level. The failure message
points the future maintainer at the correct disposition:

> If the emitter was added intentionally, this test must be removed
> AS PART OF the retirement sprint, not separately.

---

## Sprint-Level Regression Checklist

- **Invariant 1 (no broker-orphan SHORT entry):** PASS — no
  reconciliation-loop changes this session.
- **Invariant 5 (test baseline ≥ prior):** PASS — baseline 5,222 →
  after-session **5,232** (+10).
- **Invariant 14 (alert observability — backend complete):** Row "After
  Session 5b" — full pipeline E2E verified; backend complete; ready
  for Tier 3 #2 architectural review.
- **Invariant 16 (Alpaca abstinence):** PASS — `git diff --stat
  argus/data/alpaca_data_service.py` returns empty; behavioral
  anti-regression test enforces the constraint going forward.
- **Invariant 15 (do-not-modify boundaries):** PASS — only
  `argus/execution/ibkr_broker.py` modified in production code (the
  authorized site for the two emitter resolutions). No edits to
  `argus/data/alpaca_data_service.py`, `argus/execution/order_manager.py`,
  `argus/main.py`, or any other do-not-modify file.

---

## Sprint-Level Escalation Criteria

- **A1.5** (Tier 3 #2 ESCALATE) — fired AFTER this session by the
  operator (see pre-amble).
- **A2** (Tier 2 CONCERNS or ESCALATE) — pending Tier 2 verdict.
- **B1, B3, B4, B6** — none triggered.
- **C7** (E2E tests pull in event-bus + REST + WS + SQLite together —
  flakes in any layer can cascade) — no flakes observed; the new tests
  ran clean in 2.08s isolated and contributed to a 5,232-test full-suite
  green in 82.47s.

---

## Self-Assessment

**Verdict: PROPOSED_CLEAR with one MINOR_DEVIATION** (refined behavioral
Alpaca check — see Judgment Call 2 above; the literal spec test was
mutually exclusive with the do-not-modify boundary on
`alpaca_data_service.py`, and the architectural intent was preserved
via tokenize-based comment+string stripping).

**Context State: GREEN** — session completed within context limits;
all reads happened before writes; all writes verified by re-reading the
edited region and running targeted test runs before the final full
suite.

**Compaction defense:** Session was short (~9 file reads, 3 production
edits, 1 new test file). No risk of compaction-induced regression.

---

## Counter-results JSON

```json
{
  "session": "5b",
  "verdict": "PROPOSED_CLEAR",
  "minor_deviations": [
    "Refined behavioral Alpaca anti-regression test from raw substring check to tokenize-based COMMENT+STRING stripping (literal spec was mutually exclusive with do-not-modify on alpaca_data_service.py)"
  ],
  "tests_added": 10,
  "tests_added_breakdown": {
    "ibkr_disconnect_emitter": 1,
    "ibkr_disconnect_emit_does_not_raise_defensive": 1,
    "ibkr_auth_failure_emitter": 1,
    "ibkr_connection_critical_does_not_emit_auth_alert_boundary": 1,
    "e2e_databento_dead_feed_full_pipeline": 1,
    "e2e_ibkr_disconnect_with_auto_resolution": 1,
    "e2e_phantom_short_with_n_cycle_auto_resolution": 1,
    "e2e_acknowledgment_persists_restart": 1,
    "e2e_phantom_short_retry_blocked_never_auto_resolves_100_cycles": 1,
    "behavioral_alpaca_anti_regression": 1
  },
  "ibkr_emitters_resolved": [
    "_reconnect end-of-retries (DEF-014, prompt cited :453, actual current line ~570)",
    "_on_error CRITICAL non-connection branch (DEF-014, prompt cited :531, actual current site is the else-branch around :416-420)"
  ],
  "stale_line_number_disclosures": [
    "Prompt :453 actual ~:570 in _reconnect",
    "Prompt :531 actual ~:416-420 in _on_error CRITICAL else-branch (no separate TODO existed; emitter wired into existing conditional structure)"
  ],
  "alpaca_behavioral_anti_regression_passes": true,
  "alpaca_data_service_zero_edits_verified": true,
  "order_manager_zero_edits_verified": true,
  "test_baseline_pre_session": 5222,
  "test_baseline_post_session": 5232,
  "test_delta": 10,
  "tier3_2_ready": true,
  "tier3_2_invocation_required_before": "Session 5c"
}
```

---

*End Sprint 31.91 Session 5b close-out.*
