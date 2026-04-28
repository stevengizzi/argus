# Sprint 31.91 — Session 5b Tier 2 Review

**Reviewer:** Backend safety reviewer (Tier 2 automated review).
**Subject:** Session 5b implementation — IBKR emitter TODO resolutions (DEF-014) + 10 end-to-end alert-pipeline tests + behavioral Alpaca anti-regression check.
**Diff under review:** working tree (uncommitted) — `argus/execution/ibkr_broker.py` (+95/-3) + new file `tests/integration/test_alert_pipeline_e2e.py` (881 LOC, 10 tests).
**Close-out:** `docs/sprints/sprint-31.91-reconciliation-drift/session-5b-closeout.md`.
**Implementation prompt:** `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5b-impl.md`.

---

## Verdict

**CLEAR_WITH_NOTES** — recommend operator proceed to commit + invoke Tier 3 architectural review #2 on the combined 5a.1 + 5a.2 + 5b diff before Session 5c.

The single MINOR_DEVIATION (refined behavioral Alpaca check) was honestly disclosed in the close-out, technically necessary (see Finding F1 below), and preserves the architectural intent of the literal spec. No CONCERNS. No ESCALATION criteria triggered.

---

## Per-Deliverable Verdict

| Deliverable | Verdict | Evidence |
|---|---|---|
| **D10.1** — IBKR disconnect emitter (prompt `:453`, actual `~:570`) | CLEAR | `argus/execution/ibkr_broker.py:633-662` — `SystemAlertEvent(alert_type="ibkr_disconnect", severity="critical")` published at `_reconnect()` exhaustion, wrapped in try/except. Metadata includes `max_retries`, `client_id`, `host`, `port`, `detection_source`. Stale-line disclosure correctly flagged per RULE-038. |
| **D10.2** — IBKR auth emitter (prompt `:531`, actual `~:416-420 + :453-497`) | CLEAR | `argus/execution/ibkr_broker.py:422-434` adds an `else` branch on `is_connection_error` inside the CRITICAL severity handler; routes to new helper `_emit_ibkr_auth_failure_alert` at `:453-497`. Helper bridges sync→async via `asyncio.ensure_future` (matches existing pattern at `:440-447`). Stale-line disclosure correctly flagged. |
| **D10.3** — 8 E2E + behavioral Alpaca anti-regression (Test 8) + 2 mock-fixture additions | CLEAR | `tests/integration/test_alert_pipeline_e2e.py` — 10 tests across 6 classes (8 prompt tests + 2 defensive sub-tests). All 10 pass in 2.25s isolated; full suite 5,232 passing in 70.54s (matches close-out claim). |
| **D10.4** — Behavioral Alpaca anti-regression | CLEAR_WITH_NOTES (MINOR_DEVIATION, OK) | See Finding F1 below — refined from raw substring to tokenize-based COMMENT+STRING stripping. Architectural intent preserved; refinement was technically necessary. |

---

## Findings — Session-Specific Review Focus

### F1. Behavioral Alpaca anti-regression robustness (MINOR_DEVIATION → OK)

**Status:** ACCEPTED as a MINOR_DEVIATION; no escalation.

The implementer refined the prompt's literal `assert "SystemAlertEvent" not in src` to:

```python
tokens = tokenize.generate_tokens(io.StringIO(src).readline)
executable_text_chunks = [tok.string for tok in tokens if tok.type not in (tokenize.COMMENT, tokenize.STRING)]
executable_src = " ".join(executable_text_chunks)
assert "SystemAlertEvent" not in executable_src, (...)
```

**Verification (`argus/data/alpaca_data_service.py:598`):**

```
598:                    # TODO: Publish SystemAlertEvent when implemented in Sprint 5
```

The literal `"SystemAlertEvent"` substring already exists in a TODO comment in `alpaca_data_service.py`. The prompt's literal test would fail against the current state of that file. The DoD explicitly forbids modifying `alpaca_data_service.py`. The prompt's literal test was therefore **mutually exclusive with** the do-not-modify boundary — the refinement was necessary to satisfy both.

**Robustness check:** A future `import SystemAlertEvent` or `SystemAlertEvent(...)` constructor call would produce NAME tokens (not COMMENT or STRING tokens) and survive the tokenize filter — the assertion would correctly trip. The refinement preserves the semantic constraint while honoring the file boundary.

**Failure-message check (`tests/integration/test_alert_pipeline_e2e.py:875-881`):**

```
"Alpaca data service should not emit SystemAlertEvent in executable code —
queued for retirement in Sprint 31.94 (DEF-178/183). If the emitter was added
intentionally, this test must be removed AS PART OF the retirement sprint,
not separately."
```

Failure message correctly points the future maintainer at DEF-178/183 + Sprint 31.94. RULE-038 disclosure is present in the close-out (Judgment Call 2, lines 169-213).

**Verdict:** MINOR_DEVIATION accepted. Refined behavioral test is strictly more robust than the literal text-grep version while preserving the architectural intent.

### F2. E2E coverage matrix complete

**Status:** PASS, with one acknowledged gap that is acceptable.

Verified each cell in the matrix at close-out lines 282-289 against the actual test code. Each `Test N` cell has an asserting test in `tests/integration/test_alert_pipeline_e2e.py`:

- `databento_dead_feed`: Test 3 (line 469) — REST `/active`, WS `alert_active`, ack via REST, audit row, all asserted.
- `ibkr_disconnect`: Test 4 (line 547) — REST, WS, auto-resolution via `IBKRReconnectedEvent`, audit row with `audit_kind="auto_resolution"`, all asserted.
- `phantom_short`: Test 5 (line 611) — REST, WS, N-cycle auto-resolution (where N is read from config — see F3), audit row, REST `/history` archived check.
- `phantom_short_retry_blocked`: Test 7 (line 769) — 100 cycles → still active (NEVER policy verified), then operator-ack via REST.
- Persistence-survives-restart: Test 6 (line 695) — full ack + rehydrate cycle, audit row queryable post-restart.

**Acknowledged gap:** `ibkr_auth_failure` does NOT have its own dedicated end-to-end auto-resolution test. The close-out (lines 293-302) explicitly flags this and explains the gap closure: the `ibkr_auth_failure` predicate (`_ibkr_auth_success_predicate` at `argus/core/alert_auto_resolution.py:163`) consumes `(OrderFilledEvent, IBKRReconnectedEvent)` — the **same shape** as `ibkr_disconnect`'s predicate, just with one additional clearing event type. Test 4's `IBKRReconnectedEvent` clears the `ibkr_auth_failure` predicate's first leg structurally. The close-out flags this gap explicitly for Tier 3 #2 to validate.

**Verdict:** Matrix is honest; gap is acceptable and explicitly flagged.

### F3. 5-cycle threshold cross-reference (Test 5)

**Status:** PASS — strict single-source-of-truth reading verified.

`tests/integration/test_alert_pipeline_e2e.py:625-655`:

```python
threshold = (
    health_monitor._reconciliation_config
    .broker_orphan_consecutive_clear_threshold
)
assert threshold >= 1, ...
...
for cycle in range(threshold):
    await event_bus.publish(ReconciliationCompletedEvent(...))
```

`grep -n "==\s*5\|threshold" tests/integration/test_alert_pipeline_e2e.py` returns only docstrings + the runtime `threshold = ...` read. No hardcoded `5`.

**Cross-reference verified:**
- Field defined at `argus/core/config.py:346` (`ReconciliationConfig.broker_orphan_consecutive_clear_threshold: int = Field(default=5, ge=1, le=60, ...)`).
- Field is on `ReconciliationConfig`, NOT duplicated on `AlertsConfig`. `argus/core/alert_auto_resolution.py:15,112,257` all reference the canonical `ReconciliationConfig` field.
- Field consumed by 5a.2 predicate `_phantom_short_consecutive_clear_predicate` (closes via `consecutive_clear_threshold` injected from this same config field per close-out line 627-630).
- Field consumed by 2c.2's entry-gate clear (the close-out's "single source of truth" claim).

If the operator later changes the default from 5 to (say) 3 in a config tuning sprint, Test 5 will automatically fire 3 cycles instead of 5 — drift undetectable here is impossible, exactly the property the prompt's review focus #3 wanted.

**Verdict:** PASS.

### F4. NEVER auto-resolve enforcement (Test 7)

**Status:** PASS.

`tests/integration/test_alert_pipeline_e2e.py:801`:

```python
for cycle in range(100):
    await event_bus.publish(ReconciliationCompletedEvent(...))
```

**Hardcode-verification:** The `100` is real and unmistakably not a `range(1)` typo. Test docstring (line 779-783) states:

> "The 100-cycle count is intentional: it exercises the predicate enough to prove 'across many cycles, no resolution,' and is unmistakably not a 1-iteration typo."

After the 100 cycles, the assertion at line 812-814 is `still_active.state == AlertLifecycleState.ACTIVE` with the message `"phantom_short_retry_blocked must NEVER auto-resolve."` Then line 817-827 verifies operator-ack via REST clears it (proves the alert is otherwise normal — only auto-resolution is suppressed).

**Cross-reference:** `argus/core/alert_auto_resolution.py:268-281` — `phantom_short_retry_blocked` PolicyEntry uses `predicate=NEVER_AUTO_RESOLVE` (line 271). Description: `"NEVER auto-resolves; operator ack required."` — exactly the policy Test 7 pins.

**Verdict:** PASS.

### F5. `:1670-1750` IMPROMPTU-04 fix unchanged (sanity check)

**Status:** PASS.

`git diff HEAD -- argus/execution/order_manager.py | wc -l` returns `0`. The IMPROMPTU-04 fix region is structurally untouched. Working-tree diff covers only `argus/execution/ibkr_broker.py` (the authorized site for the two emitter resolutions).

`git diff --stat` confirms scope:

```
argus/execution/ibkr_broker.py | 98 ++++++++++++++++++++++++++++++++++++++++--
1 file changed, 95 insertions(+), 3 deletions(-)
```

**Verdict:** PASS.

### F6. Tier 3 #2 invocation timing

**Status:** PASS.

Close-out lines 9-30 contain a Tier 3 #2 invocation pre-amble that explicitly states:

> **Operator action required:** invoke **Tier 3 architectural review #2** on the combined 5a.1 + 5a.2 + 5b diff **BEFORE proceeding to Session 5c**. This is a phase boundary per `escalation-criteria.md` §A1.5; the alert-observability backend is sealed by Tier 3 #2, not by any individual Tier 2 verdict.

The combined-diff command is provided verbatim with the correct base SHA (`5f6b2a6`) and the full file scope. The pre-amble appears at the very top of the close-out, BEFORE the Change Manifest — operator cannot miss it.

**Verdict:** PASS — phase boundary correctly communicated.

---

## Other Verifications

### V1. Try/except wrapping prevents publish-failure propagation

- `argus/execution/ibkr_broker.py:637-662` (`_reconnect`) — `await self._event_bus.publish(...)` wrapped in `try/except Exception` with `logger.exception(...)` on failure. Defensive Test (`test_ibkr_disconnect_emit_does_not_raise_on_publish_failure` at line 339) confirms: a subscriber that raises does not propagate out of `_reconnect`.
- `argus/execution/ibkr_broker.py:488-497` (`_emit_ibkr_auth_failure_alert`) — `asyncio.ensure_future(...)` wrapped in `try/except RuntimeError` (the only documented raise condition for `ensure_future` without a running loop). Defensive: the prompt cited synchronous-callback context where this protection matters.

### V2. Sync→async bridge pattern matches existing precedent

`_emit_ibkr_auth_failure_alert` uses `asyncio.ensure_future(self._event_bus.publish(alert))` — identical pattern to the existing `OrderCancelledEvent` publish at `argus/execution/ibkr_broker.py:440-447`. Pattern conformance verified.

### V3. WebSocket fan-out contract matches handler

- `argus/api/websocket/alerts_ws.py:109` — handler calls `health_monitor.subscribe_state_changes()` and reads via `queue.get()` in the push loop (lines 128-151).
- Tests 3, 4, 5, 7 use `health_monitor.subscribe_state_changes()` to act as a synthetic WS client and `await asyncio.wait_for(ws_queue.get(), timeout=1.0)`.
- Cross-reference: `argus/core/health.py:821-836` — `subscribe_state_changes()` returns the queue; `_publish_state_change` (line 840-855) writes to all subscribers. Same surface in both paths.

### V4. Alpaca + order_manager zero-edits verification

- `git diff --stat argus/data/alpaca_data_service.py` returns empty (verified).
- `git diff --stat argus/execution/order_manager.py` returns empty (verified).

### V5. Test runtime + flake check

- Isolated: 10/10 passing in 2.25s.
- Full suite: 5,232 passing in 70.54s — matches close-out claim exactly.
- C7 (E2E flake risk per escalation criteria): no flakes observed; tests use `event_bus.drain()` + `await asyncio.sleep(0)` to deterministically settle the asyncio loop before assertions.

### V6. DoD gate-by-gate verification

| DoD Item | Verified |
|---|---|
| `:453` emitter resolved with full alert metadata payload | YES |
| `:531` emitter resolved with full alert metadata payload | YES |
| `argus/data/alpaca_data_service.py` ZERO edits | YES |
| 8 E2E + emitter tests + 2 mock updates added; all green | YES (10 tests, 8+2; mocks kept local — see Judgment Call 3) |
| Behavioral anti-regression test pins Alpaca abstinence semantically | YES |
| Test 5 specifically pins 5-cycle threshold = 2c.2's `broker_orphan_consecutive_clear_threshold` | YES |
| Test 7 specifically pins NEVER row for `phantom_short_retry_blocked` | YES |
| CI green; pytest baseline ≥ Session 5a.2 + 8 | YES (5,232 = 5,222 + 10) |

---

## Disposition of Implementer's Flagged MINOR_DEVIATION

The implementer flagged ONE MINOR_DEVIATION: refining the behavioral Alpaca check from raw substring to tokenize-based COMMENT+STRING stripping (Judgment Call 2, close-out lines 169-213).

**Disposition:** ACCEPTED as a MINOR_DEVIATION. The deviation is mechanical (one extra preprocessing step), the architectural constraint is preserved (an actual `SystemAlertEvent` constructor call would still produce NAME tokens and trip the assertion), and the alternative (modifying `alpaca_data_service.py` to delete the comment) would have violated a higher-priority do-not-modify constraint.

The disclosure is honest, in the right place (Judgment Calls section + Self-Assessment), with rationale that holds up under independent verification. RULE-011 satisfied.

---

## Sprint-Level Regression Checklist

| Invariant | Status | Note |
|---|---|---|
| Invariant 1 (no broker-orphan SHORT entry) | PASS | No reconciliation-loop changes this session. |
| Invariant 5 (test baseline ≥ prior) | PASS | 5,222 → 5,232 (+10), verified by independent re-run. |
| Invariant 14 (alert observability — backend complete) | PASS | Full pipeline E2E verified. Backend complete; ready for Tier 3 #2. |
| Invariant 15 (do-not-modify boundaries) | PASS | Only `argus/execution/ibkr_broker.py` modified; `alpaca_data_service.py` + `order_manager.py` zero edits verified. |
| Invariant 16 (Alpaca abstinence) | PASS | Behavioral test (`TestAlpacaBoundary`) enforces architectural constraint going forward. |

---

## Sprint-Level Escalation Criteria

- **A1.5** (Tier 3 #2 ESCALATE) — fires AFTER this Tier 2 verdict by the operator (recommended below).
- **A2** (Tier 2 CONCERNS or ESCALATE) — NOT triggered. Verdict is CLEAR_WITH_NOTES.
- **B1, B3, B4, B6** — none triggered.
- **C7** (E2E layer flakes) — no flakes observed.

---

## Final Verdict + Recommended Next Action

**Verdict: CLEAR_WITH_NOTES.** The "_with notes_" qualifier captures (a) the implementer's honestly-disclosed MINOR_DEVIATION on the refined behavioral Alpaca test, and (b) the matrix gap on `ibkr_auth_failure`'s dedicated E2E auto-resolution test (covered structurally by Test 4's same-shape predicate chain).

**Recommended next action:** Operator should:

1. Stage and commit the working-tree diff with a conventional commit message referencing Sprint 31.91 + Session 5b + DEF-014 resolution.
2. Stage and commit this review verdict + the close-out as separate `chore(sprint-31.91)` and `docs(sprint-31.91)` commits per the established sprint cadence.
3. **Invoke Tier 3 architectural review #2** on the combined 5a.1 + 5a.2 + 5b diff per the close-out's pre-amble (escalation-criteria.md §A1.5). Tier 3 #2 is the alert-observability backend seal; Session 5c does NOT begin until Tier 3 #2 lands.

**No remediation required.** The implementation matches spec intent at every load-bearing point that was verifiable against the actual codebase state (RULE-038), and the deviations from spec text (stale line numbers in the prompt; literal-vs-tokenize refinement on Test 8) were necessary, disclosed, and architecturally sound.

---

```json
{
  "session": "5b",
  "tier2_verdict": "CLEAR_WITH_NOTES",
  "deliverables": {
    "D10.1_disconnect_emitter": "CLEAR",
    "D10.2_auth_emitter": "CLEAR",
    "D10.3_e2e_tests": "CLEAR",
    "D10.4_behavioral_alpaca_check": "CLEAR_WITH_NOTES (MINOR_DEVIATION accepted)"
  },
  "review_focus_findings": {
    "F1_alpaca_robustness": "PASS (MINOR_DEVIATION accepted)",
    "F2_matrix_complete": "PASS (one acknowledged gap acceptable)",
    "F3_threshold_cross_reference": "PASS",
    "F4_never_auto_resolve_enforcement": "PASS",
    "F5_impromptu_04_fix_unchanged": "PASS",
    "F6_tier3_2_invocation_timing": "PASS"
  },
  "tests_added_verified": 10,
  "test_baseline_post_session_independently_verified": 5232,
  "alpaca_zero_edits_verified": true,
  "order_manager_zero_edits_verified": true,
  "remediation_required": false,
  "next_action": "operator_invoke_tier3_2_on_combined_5a.1_5a.2_5b_diff"
}
```

---

*End Sprint 31.91 Session 5b Tier 2 review.*
