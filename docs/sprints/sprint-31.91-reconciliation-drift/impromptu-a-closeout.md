# Sprint 31.91 — Impromptu A Close-Out

> **Track:** Alert Observability Backend Hardening (post-Tier-3-#2).
> **Tier 3 track marker:** `alert-observability` (continues from S5a.1 + S5a.2 + S5b).
> **Position in track:** Between Tier 3 #2 verdict (sealed Sessions 5a.1+5a.2+5b) and Session 5c (frontend integration).
> **Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition (operator-tightened routing).
> **Resolves:** DEF-217 (HIGH) + DEF-218 (MEDIUM) + DEF-219 (MEDIUM) + DEF-224 (LOW) + DEF-225 (LOW).
> **Self-assessment:** **PROPOSED_CLEAR** with **MINOR_DEVIATIONS** flagged below.
> **Mid-sprint doc-sync ref:** `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md`.
> **Anchor commit SHA:** `<filled at commit time>` (HITL-on-main; see §"Anchor commit" below).

---

## Pre-Flight Grep Verification (RULE-038)

All five impl-prompt anchors verified at session start; no drift reported:

| Anchor | Verified |
|---|---|
| `argus/data/databento_data_service.py` had exactly 1 hit for `alert_type="max_retries_exceeded"` (line 281). | ✅ |
| `argus/core/alert_auto_resolution.py` had exactly 1 hit for `alert_type="databento_dead_feed"` (line 297, in policy table). | ✅ |
| `argus/core/alert_auto_resolution.py` had `def build_policy_table` (line 236) and the `phantom_short_startup_engaged` PolicyEntry (line 303). | ✅ |
| `argus/api/routes/alerts.py` had `_AUDIT_DDL` (line 145), `_ensure_audit_table` definition (line 166), and 4 call sites (lines 219, 340, 369, 404). | ✅ |
| `tests/integration/test_alert_pipeline_e2e.py` had `class TestE2EIBKRDisconnectAutoResolution` (line 543). | ✅ |

---

## Change Manifest

### Code

- **`argus/data/databento_data_service.py`** (1 line changed) — DEF-217 fix.
  - Line 281: `alert_type="max_retries_exceeded"` → `alert_type="databento_dead_feed"`.
  - Aligns producer string with the policy-table consumer (`databento_dead_feed`),
    making the auto-resolution path active in production. Pre-fix, the policy
    entry was dead code: a real Databento dead-feed alert would have persisted
    ACTIVE forever instead of clearing on heartbeat resumption.
  - No other Databento-territory edits — surgical one-line change.

- **`argus/core/alert_auto_resolution.py`** (~28 lines added) — DEF-218 fix.
  - Two new `PolicyEntry` rows added to `build_policy_table`'s returned dict,
    inserted after `phantom_short_startup_engaged` (preserves the existing
    declaration order):
    - `eod_residual_shorts`: `NEVER_AUTO_RESOLVE` + `operator_ack_required=True`.
    - `eod_flatten_failed`: `NEVER_AUTO_RESOLVE` + `operator_ack_required=True`.
  - Both descriptions document the EOD-bounded operator-attention semantics.
  - Both producers (`argus/execution/order_manager.py`) already emit these
    alert_types; before this fix they sat ACTIVE indefinitely.
  - No predicate signatures or fields changed; no novel `PolicyEntry` shape.

- **`argus/api/routes/alerts.py`** (~30 lines deleted) — DEF-224 cleanup.
  - Deleted: `_AUDIT_DDL` constant (8 lines), `_AUDIT_INDEX_ALERT_ID` constant
    (3 lines), `_AUDIT_INDEX_TIMESTAMP` constant (3 lines), `_ensure_audit_table`
    helper function (5 lines incl. signature/docstring).
  - Deleted: 4 call sites of `await _ensure_audit_table(db)` (one per handler
    branch — `_atomic_acknowledge`, late-ack via 404 path, idempotent ACK path,
    archived-race ACK path).
  - The migration framework at `argus/data/migrations/operations.py` migration v1
    (`_migration_001_up`) now owns the `alert_acknowledgment_audit` DDL.
    Migration runs at `HealthMonitor._persist_alert` first call (lazy on
    `_ensure_operations_schema`), so the table always exists by the time any
    route handler executes in production.

### Tests

- **`tests/api/test_policy_table_exhaustiveness.py`** (NEW — 4 tests). DEF-219 regression guard.
  - `test_no_computed_alert_type_in_production` — every
    `SystemAlertEvent(alert_type=...)` construction in `argus/` uses a string
    literal (rejects variable / function-call / formatted-string values).
    Failure message points the maintainer at the structural-anchor amendment
    in `templates/implementation-prompt.md` v1.5.0.
  - `test_all_emitted_alert_types_have_policy_entries` — every emitted literal
    is a key in `build_policy_table(...)`. Catches the DEF-217 failure mode
    (producer emits, consumer's policy is dead code).
  - `test_policy_table_has_no_orphan_entries` — every policy-table key has at
    least one production emitter. Catches the inverse failure (DEF-217 was
    structurally an orphan policy entry: `databento_dead_feed` keyed but no
    producer used the string).
  - `test_argus_root_resolves` — sanity check for the directory walker.
  - Implementation: Python `ast` module parses each file in `argus/`
    (recursively), walks `Call` nodes matching `SystemAlertEvent(...)` (both
    bare `Name` and attribute-style `Attribute`), and extracts the `alert_type`
    keyword's value. Excludes `argus/core/alert_auto_resolution.py` (consumer,
    not producer) and any `__pycache__` paths. Tests in `tests/` are not
    scanned (the test for the test would be circular; the production scan is
    sufficient).

- **`tests/api/test_alerts_5a2.py`** (~5 lines changed) — exhaustiveness update.
  - `test_policy_table_is_exhaustive` updated: expected set now contains 10
    entries (the prior 8 + `eod_residual_shorts` + `eod_flatten_failed`).
  - The "NEVER entries are explicit" loop extended to include the two new
    entries.

- **`tests/integration/test_alert_pipeline_e2e.py`** (NEW class) — DEF-225 fix.
  - New `TestE2EIBKRAuthFailureAutoResolution` class with one test:
    `test_ibkr_auth_failure_clears_on_order_filled`.
  - Drives the full E2E pipeline: emit `SystemAlertEvent(alert_type="ibkr_auth_failure")`
    → consume → REST `/active` returns it → WS push (`alert_active`) →
    publish `OrderFilledEvent` → WS push (`alert_auto_resolved`) → REST
    `/active` no longer lists it → audit row with `audit_kind=auto_resolution`.
  - Closes the symmetry gap noted in S5b's pipeline-coverage matrix: Test 4
    covered the `IBKRReconnectedEvent` clearing leg of `_ibkr_auth_success_predicate`;
    this test covers the `OrderFilledEvent` clearing leg.
  - Added `OrderFilledEvent` to the test file's `from argus.core.events`
    import.

- **`tests/api/test_alerts.py`** (~22 lines added) — DEF-224 test follow-on.
  - Added `_migrate_operations_db(db_path)` helper in the helpers section
    (alongside `_seed_alert`). The helper applies the operations.db migration
    framework to the supplied path; it's a small wrapper over `apply_migrations`
    with the parent-dir `mkdir(parents=True, exist_ok=True)` guard.
  - Added one `await _migrate_operations_db(tmp_path / "operations.db")` line
    to each of the 4 route tests that hit the audit DB via `_seed_alert`
    (`test_post_alert_acknowledge_atomic_transition_writes_audit`,
    `test_post_alert_acknowledge_atomicity_rolls_back_on_commit_failure`,
    `test_post_alert_acknowledge_idempotent_200_for_already_acknowledged`,
    `test_post_alert_acknowledge_late_ack_for_archived_writes_audit`).
  - Without this, the route would no longer create the audit table on first
    write (DEF-224 deleted the lazy DDL). The migration framework normally
    runs at `HealthMonitor._persist_alert` startup; tests that bypass that
    via `_seed_alert` must apply migrations explicitly.

---

## Test Counts

**Targeted (alert observability surfaces):** 47 passed in 7.55s.

| Test file | Tests run | Result |
|---|---|---|
| `tests/api/test_policy_table_exhaustiveness.py` | 4 | All pass (NEW). |
| `tests/api/test_alerts_5a2.py` | 22 | All pass (`test_policy_table_is_exhaustive` updated to 10 entries). |
| `tests/api/test_alerts.py` | 14 | All pass (4 tests gained explicit `_migrate_operations_db` call). |
| `tests/integration/test_alert_pipeline_e2e.py` | 11 | All pass (new `TestE2EIBKRAuthFailureAutoResolution` test added). |

**New tests added in this impromptu:** 5 (4 DEF-219 guard + 1 DEF-225 E2E).

The existing `test_policy_table_is_exhaustive` absorbed DEF-218's 2 new
entries (set update) without adding a new test method, matching the impl
prompt's "approximately +4" expectation.

**Full suite:** **GREEN.** `python -m pytest --ignore=tests/test_main.py
-n auto -q` reports **5,237 passed in 66.96s** (37 warnings, all
pre-existing flake-family categories per CLAUDE.md DEF-150/167/171/190/192).
This is exactly the predicted +5 delta from the 5,232 Sprint 31.91
baseline. (Run was initially blocked mid-impromptu by `/private/tmp`
ENOSPC; operator freed disk and the suite completed clean on retry.)

---

## Mental-Revert Verification of DEF-219 Guard

To prove the regression guard would have caught DEF-217's drift, mentally
revert the DEF-217 fix (replace the `databento_dead_feed` literal in
`argus/data/databento_data_service.py` with `max_retries_exceeded`) and
re-evaluate the guard's emitted-set / policy-key set comparison:

```
emitted but not in policy:  {'max_retries_exceeded'}
in policy but not emitted:  {'databento_dead_feed'}
Mutation would FAIL:        True
```

Both `test_all_emitted_alert_types_have_policy_entries` and
`test_policy_table_has_no_orphan_entries` would fail under the mental
revert — the guard catches drift in both directions, exactly as DEF-219
intended.

---

## Judgment Calls

### 1. DEF-224: replace `_ensure_audit_table` with explicit migration calls in tests, not in the route

The impl prompt's literal edit shape said:

> 3. Find each call site of `_ensure_audit_table(db)` and delete those lines too — the migration framework's startup `apply_migrations` call now owns the table creation.

Followed literally, this would break 4 tests in `tests/api/test_alerts.py`
that bypass the production `on_system_alert_event` → `_persist_alert` →
`_ensure_operations_schema` chain via the `_seed_alert` helper. Those tests
seed alerts directly into HealthMonitor's in-memory state and then hit the
acknowledge route — but the `tmp_path/operations.db` they target was never
touched by the migration framework before the route ran.

Two implementation paths considered:

- **Path A (taken):** Delete the route's redundant DDL + helper + call sites
  per spec, AND add explicit migration calls at the test level (one
  `_migrate_operations_db(...)` line per affected test, shared helper in
  the same file). Architectural property restored: the migration framework
  is the canonical home for the schema.
- **Path B (rejected):** Inline `apply_migrations` into the route's
  `_atomic_acknowledge` and the late-ack/idempotent paths. This would
  preserve test compatibility without test edits, but at the cost of running
  migrations on every acknowledge call (idempotent but cosmetic noise) and
  centralizing schema-creation ownership inside the route layer instead of
  the framework.

Path A matches the spec's architectural intent. The tests that need explicit
migration calls were exercising production-bypass code paths; making the
production-vs-test asymmetry explicit (via `_migrate_operations_db`) is
the correct fix.

**Self-assessment:** This is a **MINOR_DEVIATION** from a literal reading
of the spec — the spec said "delete the call sites" and stopped there.
The deviation is mechanical (test-side helper added) and architectural
intent is preserved.

### 2. DEF-219 guard: one extra "sanity assertion" test (`test_argus_root_resolves`)

The impl prompt specified 3 test cases (the three exhaustiveness assertions).
I added a 4th — `test_argus_root_resolves` — as a sanity assertion that
the directory walker can find `argus/` from the test path. This guards
against the test silently scanning an empty/wrong directory and reporting
"no offenders found, all green" as a false-pass. It's 3 lines and zero
runtime cost.

**Self-assessment:** A **MINOR_DEVIATION** — the spec asked for 3 test
cases and got 4. The 4th is purely defensive infrastructure; if the
reviewer prefers it removed, removal is one-liner-revert.

### 3. DEF-218: PolicyEntry ordering in `build_policy_table`

The impl prompt's edit shape inserted the two new entries "after the
`phantom_short_startup_engaged` entry." I inserted them at the very end of
the returned dict (which is functionally identical for a Python dict;
ordering within the policy table is irrelevant to behavior). The spec's
positioning guidance is honored exactly — the new rows appear after
`phantom_short_startup_engaged`. This is not a deviation; flagged here for
completeness.

---

## Tier 2 Review (inline)

Per impl prompt §"Tier 2 Review (inline)", a Tier 2 review is conducted in
the same Claude Code session against the spec, the diff, and the new test
file. Verdict artifact at
`docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-review.md`.

---

## Definition of Done

| DoD Item | Status |
|---|---|
| Requirement 1 (DEF-217 fix) landed; producer matches policy. | ✅ |
| Requirement 2 (DEF-218) policy entries landed; table now contains 10 entries; existing exhaustiveness test updated. | ✅ |
| Requirement 3 (DEF-219) regression guard landed; new test file passes; mental-revert proves drift-detection. | ✅ |
| Requirement 4 (DEF-224) cleanup landed; routes layer no longer defines DDL; routes' acknowledge calls still work via the migration framework + test-side `_migrate_operations_db`. | ✅ |
| Requirement 5 (DEF-225) test landed; new test passes; structurally distinct from Test 4 (exercises `OrderFilledEvent` leg, not `IBKRReconnectedEvent`). | ✅ |
| Full test suite passes via `python -m pytest --ignore=tests/test_main.py -n auto -q`. | ✅ 5,237 passed in 66.96s (37 pre-existing warnings). Initially blocked mid-impromptu by `/private/tmp` ENOSPC; operator freed disk and the suite completed clean on retry. |
| Test count increases by approximately 4. | ✅ +5 (4 DEF-219 + 1 DEF-225; existing exhaustiveness test absorbed the 2 new policy entries via set update). |
| Tier 2 review verdict CLEAR. | 🔜 Pending Tier 2 review verdict. |
| Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-closeout.md`. | ✅ This file. |
| Tier 2 review at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-review.md`. | 🔜 |

---

## Sprint-Level Regression Checklist

- **Invariant 1 (no broker-orphan SHORT entry):** PASS — no
  reconciliation-loop or order-manager code touched.
- **Invariant 5 (test baseline ≥ prior):** PASS — full suite green at
  5,237 passing in 66.96s, exactly +5 from the 5,232 Sprint 31.91
  baseline. The targeted 47-test alert-observability scope is also green.
- **Invariant 14 (alert observability — backend complete):** STRENGTHENED
  — DEF-217 closes a correctness defect; DEF-218 closes a coverage gap;
  DEF-219 establishes the exhaustiveness regression guard preventing
  recurrence; DEF-224 removes the duplicate-DDL drift surface; DEF-225
  closes the predicate-symmetry test gap.
- **Invariant 15 (do-not-modify boundaries):** PASS — `argus/execution/order_manager.py`,
  `argus/execution/ibkr_broker.py`, `argus/data/alpaca_data_service.py`,
  and `argus/main.py` all unmodified. The IMPROMPTU-04 fix range and OCA
  architecture (DEC-386) are untouched.
- **Invariant 16 (Alpaca abstinence):** PASS — `argus/data/alpaca_data_service.py`
  unmodified; `TestAlpacaBoundary` test unchanged and still passing in the
  targeted run.

---

## Sprint-Level Escalation Criteria

- **A1.5** (Tier 3 ESCALATE) — N/A; this is a post-Tier-3 impromptu within
  Sprint 31.91's amended verdict scope.
- **A2** (Tier 2 CONCERNS or ESCALATE) — pending Tier 2 verdict (inline).
- **B1, B3, B4, B6** — none triggered.
- **C7** (E2E tests pull in event-bus + REST + WS + SQLite together —
  flakes in any layer can cascade) — no flakes observed; the new E2E test
  ran clean in 0.82s isolated.

---

## Self-Assessment

**Verdict: PROPOSED_CLEAR with two MINOR_DEVIATIONS:**

1. DEF-224 added a test-side `_migrate_operations_db` helper rather than
   leaving the 4 affected tests broken (Path A vs Path B in Judgment
   Call 1). Architectural intent preserved.
2. DEF-219 guard test file contains a 4th sanity-check test
   (`test_argus_root_resolves`) beyond the 3 enumerated in the spec.
   Defensive infrastructure; trivially removable if the reviewer prefers.

**Context State: GREEN** — session was short, no compaction risk; all
file reads happened before edits; targeted tests run after each requirement
landed.

**Compaction defense:** ~10 file reads, 4 production edits, 2 test edits
(1 file modification + 1 new file). Well within context limits.

---

## DEF transitions claimed

The following five DEFs are claimed as `RESOLVED-IN-SPRINT, Impromptu A`
in this close-out. Per `protocols/mid-sprint-doc-sync.md` v1.0.0, the
`OPEN-with-routing → RESOLVED` table-state transition is APPLIED at
sprint-close, when the sprint-close doc-sync reads this close-out plus
`pre-impromptu-doc-sync-manifest.md` and updates `CLAUDE.md`'s DEF table
authoritatively. This section documents the claim; sprint-close
materializes it.

| DEF | Severity | Title | Resolution evidence |
|---|---|---|---|
| **DEF-217** | HIGH | Databento dead-feed `alert_type` producer/consumer string mismatch | One-line fix at `argus/data/databento_data_service.py:281` (`"max_retries_exceeded"` → `"databento_dead_feed"`); DEF-219 regression guard prevents recurrence. |
| **DEF-218** | MEDIUM | `eod_residual_shorts` + `eod_flatten_failed` missing from auto-resolution policy table | Two `NEVER_AUTO_RESOLVE` `PolicyEntry` rows added to `build_policy_table` at `argus/core/alert_auto_resolution.py`; existing exhaustiveness test updated to 10 entries; both producers (`argus/execution/order_manager.py:2015,2050`) already emit these strings. |
| **DEF-219** | MEDIUM | Policy-table exhaustiveness invariant not enforced by tests | New `tests/api/test_policy_table_exhaustiveness.py` (4 tests) — AST-based scan of `argus/` for `SystemAlertEvent(alert_type=<literal>)` constructions; mental-revert of DEF-217 fix confirms the guard fails on drift. |
| **DEF-224** | LOW | Duplicate `_AUDIT_DDL` between routes layer and migration framework | `_AUDIT_DDL`, `_AUDIT_INDEX_*`, `_ensure_audit_table`, and 4 call sites deleted from `argus/api/routes/alerts.py`. Migration framework at `argus/data/migrations/operations.py` migration v1 is sole owner. Test-side `_migrate_operations_db` helper added to keep 4 `_seed_alert`-based route tests passing. |
| **DEF-225** | LOW | `ibkr_auth_failure` lacks dedicated E2E auto-resolution test | New `TestE2EIBKRAuthFailureAutoResolution` class in `tests/integration/test_alert_pipeline_e2e.py` covers the `OrderFilledEvent` clearing leg of `_ibkr_auth_success_predicate` (Test 4 covered the `IBKRReconnectedEvent` leg). |

Sprint-close action expected: update `CLAUDE.md`'s DEF table from
`OPEN — Routing: Sprint 31.91 Impromptu A` to `~~DEF-NNN~~ ... **RESOLVED**
(Impromptu A, 2026-04-28, anchor commit `<SHA>`)` for each row, with the
strikethrough preserving historical context per
`.claude/rules/doc-updates.md` § "Numbering Hygiene".

---

## Anchor commit

| Field | Value |
|---|---|
| Anchor commit SHA | `<filled at commit time>` |
| Branch | `main` (HITL on main per Sprint 31.91 mode) |
| Commit subject pattern | `feat(sprint-31.91): Impromptu A — alert observability hardening (DEF-217/218/219/224/225)` |
| Co-author | Claude (Anthropic) per project commit-style convention |

The sprint-close doc-sync should read this SHA and propagate it to:

- `CLAUDE.md` DEF table (RESOLVED rows for DEF-217/218/219/224/225 with
  the SHA in the resolution evidence column).
- `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md`
  (Impromptu A row in Sessions Complete + test-tally + condition tracker).
- `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md`
  (Impromptu A landed-CLEAR row).

---

## Counter-results JSON

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "31.91",
  "session": "Impromptu-A",
  "mid_sprint_doc_sync_ref": "docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md",
  "verdict": "COMPLETE",
  "tests": {
    "before": 5232,
    "after": 5237,
    "new": 5,
    "all_pass": true,
    "pytest_count": 5237,
    "vitest_count": 866
  },
  "files_created": [
    "tests/api/test_policy_table_exhaustiveness.py",
    "docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-closeout.md",
    "docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-review.md"
  ],
  "files_modified": [
    "argus/data/databento_data_service.py",
    "argus/core/alert_auto_resolution.py",
    "argus/api/routes/alerts.py",
    "tests/api/test_alerts.py",
    "tests/api/test_alerts_5a2.py",
    "tests/integration/test_alert_pipeline_e2e.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "Test-side `_migrate_operations_db` helper added to tests/api/test_alerts.py",
      "justification": "DEF-224 deletion of route's lazy `_ensure_audit_table` would have broken 4 _seed_alert-based route tests; explicit migration call at the test level makes the production-vs-test asymmetry explicit while preserving the spec's architectural intent."
    },
    {
      "description": "Sanity-check test `test_argus_root_resolves` in tests/api/test_policy_table_exhaustiveness.py",
      "justification": "Defensive 3-line test that guards the directory walker against silent false-passes if argus/ becomes unreachable from the test path."
    }
  ],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "DEF-220 (acknowledgment_required_severities consumer wiring) remains routed to Session 5c per Tier 3 #2 verdict — folded INTO 5c, not a precondition for 5c entry.",
    "DEF-221 (DatabentoHeartbeatEvent producer wiring) remains routed to Impromptu B per Tier 3 #2 verdict; Impromptu A's DEF-217 fix is a structural prerequisite for Impromptu B's end-to-end auto-resolution validation."
  ],
  "doc_impacts": [
    {
      "document": "CLAUDE.md",
      "change_description": "Update DEF table to mark DEF-217, DEF-218, DEF-219, DEF-224, DEF-225 as RESOLVED-IN-SPRINT (Impromptu A) at sprint-close per pre-impromptu-doc-sync-manifest.md."
    },
    {
      "document": "docs/decision-log.md",
      "change_description": "DEC-388 (alert observability architecture) materializes at sprint-close incorporating Impromptu A outcomes — extended policy table to 10 entries, regression guard established, route-layer DDL duplication removed, ibkr_auth_failure E2E coverage closed."
    },
    {
      "document": "docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md",
      "change_description": "Refresh test tally + Impromptu A row + condition tracker (Impromptu A landed CLEAR pending Tier 2)."
    }
  ],
  "dec_entries_needed": [],
  "warnings": [
    "Mid-impromptu /private/tmp ENOSPC briefly blocked Bash invocations; operator freed disk space and the full suite completed clean on retry. Recorded for post-mortem context only."
  ],
  "implementation_notes": "DEF-224's literal spec interpretation (delete call sites with no replacement) would have broken 4 _seed_alert-based route tests in tests/api/test_alerts.py. Took the architectural-intent-preserving path: deleted the route-side DDL/helper/call sites per spec, AND added a test-side `_migrate_operations_db` helper for the affected tests. Migration framework remains the canonical home for the schema; the test-side helper makes the production-vs-test asymmetry explicit (production runs migrations at HealthMonitor startup; tests that bypass that path via _seed_alert must apply migrations themselves)."
}
```
