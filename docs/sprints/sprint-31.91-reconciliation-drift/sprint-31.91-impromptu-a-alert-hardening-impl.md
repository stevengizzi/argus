# Sprint 31.91 — Impromptu A Implementation Prompt: Alert Observability Hardening

> **Workflow contract:** authored under `templates/implementation-prompt.md` v1.5.0 (structural anchors); references `protocols/mid-sprint-doc-sync.md` v1.0.0 for closeout discipline.
> **Sprint:** 31.91 reconciliation-drift.
> **Position in track:** between Tier 3 #2 verdict and Session 5c.
> **Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition.
> **Resolves:** DEF-217 (HIGH) + DEF-218 (MEDIUM) + DEF-219 (MEDIUM) + DEF-224 (LOW) + DEF-225 (LOW).
> **Tier 2 review:** inline within this implementing session.

## Pre-Flight

Before making any edits, run all grep-verify commands listed in "Files to Modify" below. Report any drift in the close-out under RULE-038. If any anchor cannot be located, HALT and request operator disposition.

Read the following inputs in full:
- This impl prompt.
- `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended; Concerns A, B, D, E + Item 1).
- `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md` (latest state).
- `argus/core/alert_auto_resolution.py` (in full — the policy table is the central artifact).
- `argus/data/databento_data_service.py` (in full — DEF-217 fix site).
- `argus/api/routes/alerts.py` (DEF-224 cleanup site).
- `tests/integration/test_alert_pipeline_e2e.py` (DEF-225 test addition site; existing test patterns).
- `tests/api/test_alerts_5a2.py` (existing policy-table test patterns).

## Scope

Five items, all touching the alert observability backend that Tier 3 #2 just sealed. Bundled into one impromptu because they share file context.

### Requirement 1 — DEF-217: Fix Databento alert_type string mismatch

**Anchor:** in `argus/data/databento_data_service.py`, the production `SystemAlertEvent` construction with `alert_type="max_retries_exceeded"`.

**Pre-flight grep-verify:**
```bash
grep -n 'alert_type="max_retries_exceeded"' argus/data/databento_data_service.py
# Expected: 1 hit (the dead-feed emitter)

grep -n 'alert_type="databento_dead_feed"' argus/core/alert_auto_resolution.py
# Expected: 1 hit (the policy table entry)
```

**Edit shape:** replace the literal string `"max_retries_exceeded"` with `"databento_dead_feed"` in the SystemAlertEvent construction.

**Justification:** the policy table at `argus/core/alert_auto_resolution.py` keys on `databento_dead_feed`; the spec D9b auto-resolution policy table also says `databento_dead_feed`. The `max_retries_exceeded` string is a pre-Sprint-31.91 emitter value that was missed during S5a.1's metadata migration. This fix aligns the producer string with the consumer policy.

### Requirement 2 — DEF-218: Add eod_residual_shorts + eod_flatten_failed to policy table

**Anchor:** in `argus/core/alert_auto_resolution.py`, the `build_policy_table` function's returned dictionary.

**Pre-flight grep-verify:**
```bash
grep -n "def build_policy_table" argus/core/alert_auto_resolution.py
grep -n '"phantom_short_startup_engaged":' argus/core/alert_auto_resolution.py
# Expected: 1 hit each
```

**Edit shape:** add two new `PolicyEntry` rows to the returned dict, after the `phantom_short_startup_engaged` entry. Both use `NEVER_AUTO_RESOLVE` predicate and `operator_ack_required=True`.

```python
        "eod_residual_shorts": PolicyEntry(
            alert_type="eod_residual_shorts",
            consumes_event_types=(),
            predicate=NEVER_AUTO_RESOLVE,
            operator_ack_required=True,
            description=(
                "NEVER auto-resolves; operator ack required. EOD-bounded "
                "short residue (Sprint 30 deferred residue); operator "
                "should review before next session."
            ),
        ),
        "eod_flatten_failed": PolicyEntry(
            alert_type="eod_flatten_failed",
            consumes_event_types=(),
            predicate=NEVER_AUTO_RESOLVE,
            operator_ack_required=True,
            description=(
                "NEVER auto-resolves; operator ack required. Failed EOD "
                "flatten — positions remain at session close, requires "
                "operator attention before next session."
            ),
        ),
```

### Requirement 3 — DEF-219: Add policy-table exhaustiveness regression guard

**New file:** `tests/api/test_policy_table_exhaustiveness.py`

The test scans production code (`argus/`) for `SystemAlertEvent(alert_type=<literal>)` and `SystemAlertEvent(...; alert_type=<literal>)` constructions, extracts the literal string values, and asserts each is a key in `build_policy_table(...)`.

**Implementation approach:** use Python's `ast` module to parse production source files and walk the AST for `Call` nodes where the func name matches `SystemAlertEvent`. For each such Call node, find the keyword argument `alert_type=` and extract the literal string value (only literal strings — `ast.Constant` nodes with `value` of type `str`). Reject computed `alert_type` values (non-literal) — the test should fail if any are encountered, with a message explaining that all alert_types must be statically resolvable.

**Test cases:**
1. `test_all_emitted_alert_types_have_policy_entries` — scans production code, builds the set of emitted alert_types, asserts each is a policy-table key.
2. `test_no_computed_alert_type_in_production` — asserts every `SystemAlertEvent(alert_type=...)` construction uses a string literal (not a variable, function call, etc.). Failure message points the maintainer at the structural-anchor amendment in `templates/implementation-prompt.md` v1.5.0.
3. `test_policy_table_has_no_orphan_entries` — the inverse direction: every policy-table key has at least one production emitter (test files excluded). This catches dead-code policy entries — which is what DEF-217 was, before the fix.

**Test scope:** scans `argus/` directory recursively, excludes `argus/core/alert_auto_resolution.py` itself (the policy table is the consumer, not a producer of its own keys), and excludes any `tests/` subdirectories.

### Requirement 4 — DEF-224: Remove duplicate _AUDIT_DDL from routes layer

**Anchor:** in `argus/api/routes/alerts.py`, the module-level `_AUDIT_DDL` string constant and the `_ensure_audit_table` helper function.

**Pre-flight grep-verify:**
```bash
grep -n "^_AUDIT_DDL\|^async def _ensure_audit_table" argus/api/routes/alerts.py
# Expected: 2 hits (the constant + the function)

grep -n "_ensure_audit_table" argus/api/routes/alerts.py
# Expected: definition + 2-3 call sites
```

**Edit shape:**
1. Delete the `_AUDIT_DDL` module constant.
2. Delete the `_ensure_audit_table` helper function.
3. Find each call site of `_ensure_audit_table(db)` and delete those lines too — the migration framework's startup `apply_migrations` call now owns the table creation.

**Verification that the framework owns it:** `argus/data/migrations/operations.py` migration v1's `_migration_001_up` includes `_ALERT_ACK_AUDIT_DDL`. This migration runs at HealthMonitor startup (before any route handler can be hit), so the table always exists by the time the routes execute.

### Requirement 5 — DEF-225: Add dedicated ibkr_auth_failure E2E test

**Anchor:** in `tests/integration/test_alert_pipeline_e2e.py`, after the existing `TestE2EIBKRDisconnectAutoResolution` class.

**Pre-flight grep-verify:**
```bash
grep -n "class TestE2EIBKRDisconnectAutoResolution" tests/integration/test_alert_pipeline_e2e.py
# Expected: 1 hit
```

**Edit shape:** add a new test class `TestE2EIBKRAuthFailureAutoResolution` with one test method exercising the `OrderFilledEvent` clearing leg of the `_ibkr_auth_success_predicate`:

```python
class TestE2EIBKRAuthFailureAutoResolution:
    """E2E test for ibkr_auth_failure auto-resolution via OrderFilledEvent.

    Closes the symmetry gap noted in S5b closeout — Test 4 covered
    the IBKRReconnectedEvent leg; this test covers the OrderFilledEvent
    leg of the same predicate. Surfaced as DEF-225 by Tier 3 #2.
    """

    async def test_ibkr_auth_failure_clears_on_order_filled(...):
        # 1. Emit SystemAlertEvent(alert_type="ibkr_auth_failure")
        # 2. Verify alert is ACTIVE via REST /alerts/active
        # 3. Verify WS push fires (alert_active)
        # 4. Publish OrderFilledEvent
        # 5. Verify alert auto-resolves (alert_auto_resolved WS push)
        # 6. Verify REST /alerts/active no longer lists it
        # 7. Verify audit_log row with audit_kind="auto_resolution"
```

Use the existing fixture pattern from `TestE2EIBKRDisconnectAutoResolution` for setup.

## Scope Boundaries (do-not-modify)

- `argus/execution/order_manager.py` — zero edits this impromptu.
- `argus/execution/ibkr_broker.py` — zero edits this impromptu.
- `argus/data/alpaca_data_service.py` — zero edits (DoD invariant from Sprint 31.91).
- `argus/main.py` — zero edits (no scoped exception this impromptu).
- The IMPROMPTU-04 fix range and OCA architecture (DEC-386) — invariant 15 still applies.

## Tier 2 Review (inline)

After implementation, spawn a Tier 2 review subagent within this same Claude Code session. The reviewer reads:
- This impl prompt.
- The diff produced.
- The new test file.
- `tier-3-review-2-verdict.md` (amended) for context.

Review focus areas:
1. DEF-217 fix is the minimal one-line change (no scope creep into other Databento territory).
2. DEF-218 policy entries follow the existing PolicyEntry shape (no novel fields).
3. DEF-219 regression guard handles edge cases (no false positives on test files; correct handling of `SystemAlertEvent` construction patterns; clear failure messages).
4. DEF-224 deletion is complete (no orphan references to `_AUDIT_DDL` or `_ensure_audit_table`).
5. DEF-225 test exercises the OrderFilledEvent leg specifically (not redundant with Test 4).

Verdict format: structured JSON per `schemas/structured-review-verdict-schema.md`.

## Definition of Done

- [ ] Requirement 1 (DEF-217 fix) landed; grep-verify post-fix confirms `databento_dead_feed` matches between emitter and policy.
- [ ] Requirement 2 (DEF-218 policy entries) landed; policy table now contains 10 entries; existing exhaustiveness test updated to match.
- [ ] Requirement 3 (DEF-219 regression guard) landed; new test file passes; running it WITHOUT requirements 1+2 in place would fail (verifying the guard actually catches drift).
- [ ] Requirement 4 (DEF-224 cleanup) landed; routes layer no longer defines DDL; routes' acknowledge calls still work via the migration framework's startup-time table creation.
- [ ] Requirement 5 (DEF-225 test) landed; new test passes; structurally distinct from Test 4 (exercises OrderFilledEvent leg, not IBKRReconnectedEvent).
- [ ] Full test suite passes: `python -m pytest --ignore=tests/test_main.py -n auto -q`.
- [ ] Test count increases by approximately 4 (3 new tests in DEF-219 guard + 1 in DEF-225 + 0-1 in DEF-218 — the existing exhaustiveness test absorbs the 2 new policy entries).
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-closeout.md`.
- [ ] Tier 2 review at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-review.md`.

## Closeout requirements

The close-out must include the structured fields per `schemas/structured-closeout-schema.md` plus:
- `mid_sprint_doc_sync_ref: "docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md"` (per `protocols/mid-sprint-doc-sync.md` v1.0.0).
- DEF transitions claimed: DEF-217, DEF-218, DEF-219, DEF-224, DEF-225 → all "RESOLVED-IN-SPRINT, Impromptu A" (status transition applied at sprint-close per the manifest).
- Anchor commit SHA for the impromptu's implementation.
- Tier 3 track marker: `alert-observability` (continues from S5a.1+S5a.2+S5b).
