# Sprint 31.91 — Session 5a.1 Tier 2 Review

**Reviewer:** Tier 2 (Claude Opus 4.7 1M, read-only)
**Reviewed commit:** `0236e27` (parent: `e847cde`)
**Review date:** 2026-04-28

---BEGIN-REVIEW---

## Verdict: **CLEAR**

Session 5a.1 delivers exactly the scope laid out in `sprint-31.91-session-5a.1-impl.md`: the eight requirements (R0 emitter migration, R0.5 EOD verify rewrite, R1 AlertsConfig, R2 HealthMonitor consumer, R3 main.py subscription, R4 alerts REST, R5 router registration, doc update). All acceptance grep / tests pass, do-not-modify regions are confirmed clean, atomicity contract is exercised by a dedicated test, all four idempotency paths are covered with correct `audit_kind` values.

A small bookkeeping discrepancy (closeout reports +21 tests; actual delta is +18) is noted but is non-blocking — the regression invariant (count ≥ baseline) holds with significant margin.

## Test Results

```
python -m pytest --ignore=tests/test_main.py -n auto -q
→ 5202 passed, 0 failed, 34 warnings in 66.25s (0:01:06)
```

Pre-session baseline (verified by checking out `e847cde` and recollecting): **5184 tests**.
Post-session count: **5202 tests**. Net delta: **+18 tests**.

Per-file breakdown:
- `tests/api/test_alerts.py` (NEW): 12 tests
- `tests/core/test_events.py`: +2 tests (16 collected total; was 14)
- `tests/execution/order_manager/test_def214_eod_verify.py` (NEW): 4 tests
- Total net new: **18**

The closeout's `tests_added: 21` and the kickoff brief's "5200 → 5202" baseline are both off (by 3 and 16 respectively) — see Finding F1 below. Invariant 5 (count ≥ pre-session baseline) PASSES regardless: 5202 ≥ 5184. RULE-038 sub-bullet "kickoff statistics in close-outs" applies.

Targeted reruns:
- `pytest tests/api/test_alerts.py -v` → 12 passed in 2.50s
- `pytest tests/execution/order_manager/test_def214_eod_verify.py -v` → 4 passed in 2.30s
- `pytest tests/core/test_events.py -q` → 16 passed
- `pytest tests/core/test_health.py -q` → 20 passed (C7 escalation NOT triggered)
- `pytest tests/execution/order_manager/test_def199_eod_short_flip.py -q` → 6 passed (DEF-199 regression intact)
- `pytest tests/docs/test_architecture_api_catalog_freshness.py -v` → 4 passed (catalog freshness OK)
- `pytest tests/api/test_alerts.py::TestAcknowledgeAlert::test_post_alert_acknowledge_atomicity_rolls_back_on_commit_failure -v` → 1 passed

## Do-Not-Modify Region Verification

All confirmed via `git diff e847cde..HEAD -- <region>` returning empty:

- ✅ `argus/models/trading.py` — no diff
- ✅ `argus/execution/alpaca_broker.py` — no diff
- ✅ `argus/data/alpaca_data_service.py` — no diff
- ✅ `argus/execution/ibkr_broker.py` — no diff
- ✅ `argus/execution/broker.py` — no diff
- ✅ `argus/core/risk_manager.py` — no diff
- ✅ `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` — no diff
- ✅ `workflow/` — no diff
- ✅ `argus/execution/order_manager.py:1670-1750` — no diff in this range; modifications are at hunks `@@ -1992`, `@@ -2019`, `@@ -2335` (post-Pass-2 verification block + `_emit_cancel_propagation_timeout_alert` metadata addition). The 1670-1750 range covers EOD Pass 1 + margin-circuit reset; untouched.
- ✅ `argus/main.py` — single SystemAlertEvent subscription line added at L411-419 (scoped exception per invariant 15). IMPROMPTU-04 `check_startup_position_invariant()` and `_startup_flatten_disabled` flag at L124, L198-202, L377-398, L1158 all unchanged.

## Atomic Transition Contract (Review Focus #1)

### Implementation: `_atomic_acknowledge` at `argus/api/routes/alerts.py:197-242`

Pattern verified:

1. Snapshot pre-mutation state (`pre_state`, `pre_ack_at`, `pre_ack_by`, `pre_ack_reason`) at L212-215, **BEFORE** entering the `aiosqlite.connect()` context manager.
2. Inside try block within the connection context:
   a. `_ensure_audit_table(db)` — DDL (idempotent, may implicitly commit any prior open txn; non-load-bearing).
   b. `_insert_audit_row(...)` returns `lastrowid` (writes to SQLite journal but not committed yet under deferred-mode default).
   c. `health_monitor.apply_acknowledgment(...)` — pure attribute assignment on the `ActiveAlert` instance (cannot raise in current implementation).
   d. `await db.commit()` — if this raises, control transfers to except block.
3. Except block (L235-241): reverts the four in-memory fields to the pre-mutation snapshot, then `raise`. The connection's pending INSERT is rolled back when the `aiosqlite.connect` context manager closes (uncommitted journal entries are dropped by SQLite).

### Test verification: `test_post_alert_acknowledge_atomicity_rolls_back_on_commit_failure` at `tests/api/test_alerts.py:299-353`

Test pattern: patches `aiosqlite.Connection.commit` to raise `RuntimeError`, calls `_atomic_acknowledge` directly, asserts:
- `RuntimeError` propagates (no swallow).
- `alert.state == AlertLifecycleState.ACTIVE` (rollback).
- `alert.acknowledged_at_utc / acknowledged_by / acknowledgment_reason` all `None`.
- `alert_acknowledgment_audit` row count == 0 for the alert ID (or table doesn't exist).

**Verdict: contract satisfied.** The order of operations is correct, snapshot-then-mutate-then-commit pattern is sound, the rollback test is meaningful (it actively patches `commit` to fail and asserts on observable state). Note that the test calls the helper directly rather than going through FastAPI's exception handling, which is the cleaner choice — it isolates the atomicity logic from HTTP-layer concerns.

A subtle correctness point worth recording: if `apply_acknowledgment` is ever extended to do work that could partially fail mid-mutation, the snapshot-restore in the except block still recovers cleanly because all four fields are unconditionally reverted (not contingent on which mutation step failed). Future-proof.

## Idempotency: All Four Paths

| Path | Status | audit_kind | Test |
|------|--------|-----------|------|
| Normal (ACTIVE → ACKNOWLEDGED) | 200 | `"ack"` | `test_post_alert_acknowledge_atomic_transition_writes_audit` ✅ |
| Idempotent (already ACKNOWLEDGED) | 200, original acker preserved | `"duplicate_ack"` | `test_post_alert_acknowledge_idempotent_200_for_already_acknowledged` ✅ |
| Late-ack (already ARCHIVED) | 200 with `state="archived"` | `"late_ack"` | `test_post_alert_acknowledge_late_ack_for_archived_writes_audit` ✅ |
| Unknown ID | 404, no audit row | (none) | `test_post_alert_acknowledge_404_for_unknown_id` ✅ |

Notable: the route has TWO late-ack code paths (one at L338-364 for IDs only in `_alert_history` with `state==ARCHIVED`; one at L402-421 for IDs in `_active_alerts` whose state is `ARCHIVED`). Per closeout J4, 5a.1 never *produces* an `_active_alerts` entry with `ARCHIVED` state — but the defensive branch at L402 handles the case where 5a.2's auto-resolution mutates a `_active_alerts` entry's state in-place. Both paths emit `audit_kind="late_ack"` and return `state="archived"`. Solid forward-compat design.

## Architectural Findings

### F1. Test count bookkeeping mismatch (cosmetic)
- **Source:** `session-5a.1-closeout.md:73` claims "21 net new tests"; closeout JSON `tests_added: 21`. The kickoff brief states "Pre-session was 5200; post-session is 5202".
- **Actual:** Pre-session baseline 5184; post-session 5202; net delta **18** (12+2+4).
- **Severity:** Cosmetic. Invariant 5 holds with margin.
- **Recommendation:** future closeouts should grep the diff for new `def test_` lines as a sanity check (Universal RULE-038 sub-bullet "kickoff statistics in close-outs"). The kickoff brief's "5200" should be corrected if Sprint 31.91 has any future runs that re-cite it.

### F2. `get_archived_alert_by_id` linear scan over history (acknowledged in closeout)
- **Source:** `argus/core/health.py:490-503`.
- **Cost:** O(N) over `_alert_history` (capped at 1000). Worst case: late-ack on the oldest archived ID scans the full window.
- **Severity:** LOW. In-memory, bounded, single-operator system. Latency is tens of microseconds.
- **Recommendation:** Session 5a.2 should replace with SQLite-indexed lookup as planned.

### F3. In-memory state loss on restart (acknowledged in closeout)
- **Source:** `argus/core/health.py:173-175` — `_active_alerts` and `_alert_history` are not persisted in 5a.1.
- **Severity:** Documented and accepted for 5a.1. Sprint-level invariant 14 explicitly defines 5a.1 as "in-memory only".
- **Recommendation:** Session 5a.2 must persist alerts BEFORE mutating `_active_alerts`, otherwise an alert fire-and-forget'd via EventBus (`asyncio.create_task` style) could be silently dropped on a restart that occurs between dispatch and consumer execution. This is a 5a.2 design constraint, not a 5a.1 bug.

### F4. Fire-and-forget event dispatch (informational)
- **Source:** EventBus dispatches handlers as background asyncio tasks; `event_bus.drain()` is the test idiom.
- **Production behavior:** if the loop drops a dispatch task before `on_system_alert_event` runs (e.g. system shutting down mid-publish), the alert is silently lost. This is consistent with how all SystemAlertEvent consumers behave today.
- **Severity:** Acceptable for 5a.1 in-memory state.
- **Recommendation:** 5a.2 persistence design should consider whether emit-time persistence (alert written to DB by emitter, then HealthMonitor catches up via subscription) is warranted to close this gap. This crosses producer/consumer boundaries and may be out of scope; flagging for 5a.2 design discussion.

### F5. 200-with-state="archived" instead of HTTP 409 (closeout J1)
- **Source:** route returns 200 with `state="archived"` for late-ack instead of 409.
- **Assessment:** Acceptable. The judgment is well-reasoned (operator's request succeeded, audit row written, frontend routes on `state` field). 409 would imply rejection, which is misleading. Aligns with REST principle that idempotent operations should not surface conflict errors when the outcome is acceptable.
- **Recommendation:** none — the choice is documented and the audit log preserves forensic information.

### F6. `eod_verify_*_seconds` Pydantic bounds vs. test bypass (informational)
- **Source:** `OrderManagerConfig` constrains `eod_verify_timeout_seconds: float = Field(ge=5.0, le=120.0)` and `eod_verify_poll_interval_seconds: float = Field(ge=0.5, le=5.0)`. Tests use `object.__setattr__` to bypass these for sub-second testing.
- **Assessment:** Standard pattern; production validators remain in place. The test code annotates this clearly at `test_def214_eod_verify.py:104-110`. No risk of bypass leaking into production.
- **Recommendation:** none.

### F7. EOD verify polling residual_shorts last-snapshot semantics (informational)
- **Source:** `_verify_eod_flatten_complete` at `order_manager.py:2096-2157`. The polling loop breaks on `not failed_longs`; `residual_shorts` reflects only the LAST snapshot.
- **Assessment:** Correct. Shorts in this codebase represent the broker's persistent state that ARGUS does not flatten — they don't disappear without operator intervention. If a flip occurs (long becomes short via OCA race), it surfaces in the last snapshot. No risk.
- **Recommendation:** none. Could merit an inline comment noting "residual_shorts reflects last snapshot only", but cosmetic.

### F8. Alerts REST routes are JWT-only (no rate limiting)
- **Source:** all three routes use `Depends(require_auth)`; no throttling layer.
- **Assessment:** Acceptable for single-operator system; consistent with rest of `argus/api/routes/`. The acknowledge endpoint writes to `data/operations.db` per request, which is bounded by operator typing speed.
- **Recommendation:** none. If alert volume escalates in 5a.2 to tens of alerts/sec, consider a per-route throttle.

## Risk Register

No new risks introduced. Existing patterns reused:
- aiosqlite connection lifecycle: identical to Session 2c.1's `phantom_short_gated_symbols` pattern (same `data/operations.db`, same idempotent DDL, same context-manager-based connection cleanup).
- JWT auth: identical to all other `/api/v1/` routes.
- Pydantic validation: standard model with field constraints; test bypass via `object.__setattr__` is local to test scope.
- Pydantic test bypass via `object.__setattr__`: documented pattern, used in 4 lines of test code.

## Sprint-Level Regression Checklist

| Invariant | Status | Notes |
|-----------|--------|-------|
| 5 (count ≥ baseline) | ✅ PASS | 5202 ≥ 5184 (margin +18) |
| 9 (IMPROMPTU-04 unchanged) | ✅ PASS | `check_startup_position_invariant` and `_startup_flatten_disabled` flag both intact at expected line numbers |
| 14 (5a.1 = consumer + REST + ack in-memory) | ✅ PASS | Matches delivered scope |
| 15 (main.py untouched except scoped exception) | ✅ PASS | Single 8-line subscription block at L411-419, co-located with HealthMonitor.start() call, no other main.py edits |

## Sprint-Level Escalation Criteria

| Criterion | Triggered? | Notes |
|-----------|-----------|-------|
| A2 (Tier 2 verdict CONCERNS or ESCALATE) | NO | This review is CLEAR |
| B1, B3, B4, B6 (standard halt) | NO | None observed |
| C5 (main.py edit scope) | NO | Single subscription line, scoped exception, IMPROMPTU-04 untouched |
| C7 (HealthMonitor regressions) | NO | All 20 `test_health.py` tests pass |

## Recommendations for Subsequent Sessions

### Session 5a.2 (persistence + auto-resolution)
1. **Persist on consume, not on ack.** When `on_system_alert_event` fires, write the alert to SQLite synchronously before mutating `_active_alerts`. This closes Finding F4 (silent loss on shutdown-mid-dispatch).
2. **Replace `get_archived_alert_by_id` linear scan** with an indexed query against the persisted alert table (Finding F2).
3. **Define auto-resolution policy table.** The closeout flags `phantom_short_retry_blocked` and `cancel_propagation_timeout` as candidates that may NOT auto-archive. The policy doc should be a YAML map under `AlertsConfig` so operator tuning doesn't require code changes.
4. **Schema migration plan.** `data/operations.db` currently has the audit table created idempotently per-request. Adding a `system_alerts` table for persisted alerts should follow the same idempotent DDL pattern (no migrations infrastructure needed).
5. **Audit-log retention.** `AlertsConfig.audit_log_retention_days` is hinted in the 5a.1 docstring but not implemented. 5a.2 should add a periodic prune task (mirrors evaluation.db pattern).

### Session 5b (auto-resolution policy)
1. The `AlertsConfig.acknowledgment_required_severities` gate is wired but not yet consumed. 5b should make `["critical"]` block the auto-archive path while `["info", "warning"]` proceed unless held by another condition.
2. Cross-link with the `eod_residual_shorts` (warning) and `eod_flatten_failed` (critical) emitters introduced in 5a.1 — both fire from the same origin, so policy decisions should compose cleanly.

### Session 5c-5e (frontend banner + audit-log search)
1. The `metadata` dict is now structurally populated on every emitter. Frontend can route on `metadata.category`, `metadata.symbol`, `metadata.shares`, etc. without parsing `message`.
2. Historical late-ack logic should display the original acknowledger info (preserved in `acknowledged_by`) so the operator sees who acked first.

## Notes on Closeout Quality

The session-5a.1-closeout.md is comprehensive and self-aware. Judgment calls J1-J4 are clearly documented. The "Notes for Tier 2 Reviewer" section at L174-186 was substantively useful — items 1-6 were all directly verifiable and verified.

Bookkeeping nit: `tests_added: 21` in the JSON should be `18` (Finding F1).

---END-REVIEW---

```json:structured-verdict
{
  "session": "5a.1",
  "verdict": "CLEAR",
  "tests_pre_session_baseline": 5184,
  "tests_post_session": 5202,
  "tests_net_delta": 18,
  "closeout_tests_added_claim": 21,
  "closeout_count_discrepancy_severity": "cosmetic",
  "donotmodify_violations": 0,
  "main_py_scoped_exception_validated": true,
  "improptu_04_invariant_intact": true,
  "atomic_transition_contract_verified": true,
  "idempotency_paths_verified": ["normal_ack", "duplicate_ack", "late_ack_archived", "404_unknown"],
  "all_emitters_have_metadata": true,
  "emitter_count_with_metadata": 11,
  "review_focus_areas_verified": [
    "atomic_transition",
    "idempotency_edge_cases",
    "fire_and_forget_dispatch_acknowledged",
    "no_operator_case_via_ack_required_severities",
    "in_memory_state_discipline",
    "subscription_wiring_co_location",
    "alerts_config_yaml_loadability"
  ],
  "regression_checks": {
    "test_health_py": "20 passed",
    "test_def199_eod_short_flip_py": "6 passed",
    "test_architecture_freshness": "4 passed",
    "full_suite": "5202 passed in 66.25s"
  },
  "escalation_criteria_triggered": [],
  "tier_3_track": "alert-observability",
  "context_state": "GREEN",
  "recommendations_for_next_sessions": {
    "5a.2": [
      "persist on consume not on ack (closes F4)",
      "replace get_archived_alert_by_id linear scan with indexed query (F2)",
      "auto-resolution policy as YAML map under AlertsConfig",
      "idempotent DDL for system_alerts table",
      "audit-log retention periodic prune"
    ],
    "5b": [
      "wire acknowledgment_required_severities gate to block auto-archive for critical",
      "compose policy with eod_residual_shorts + eod_flatten_failed emitter pair"
    ],
    "5c-5e": [
      "frontend routes on metadata.category structurally",
      "display original acknowledger from preserved acknowledged_by"
    ]
  }
}
```
