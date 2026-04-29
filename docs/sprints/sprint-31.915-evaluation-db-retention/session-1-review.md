# Sprint 31.915 — Session 1 Tier 2 Review

**Sprint:** 31.915 — `evaluation.db` Retention Mechanism + Observability
**Session:** 1 (single-session impromptu, full-protocol)
**Reviewer:** Tier 2 (read-only)
**Pre-session SHA:** `84d072b`
**Post-session SHA:** `e58edec` (impl) → `15f6746` (closeout SHA-anchor)
**Diff range:** `git diff 84d072b..HEAD`
**Date:** 2026-04-29

---

## ---BEGIN-REVIEW---

## 1. Verdict at a glance

**CLEAR.** All 8 session-specific review focus items pass. All sprint-level
regression checklist items pass. No escalation criterion is triggered. The
implementation is honest about its deviation from the spec's H1-prescribed
fix shape — Phase A conclusively ruled out H1 and confirmed H3, and the
adopted fix (deletion-INFO BEFORE `await self._vacuum()`) is the H3-correct
version that the spec author explicitly authorized.

`5279 passed, 36 warnings in 70.21s` against the full suite —
`python -m pytest --ignore=tests/test_main.py -n auto -q` exits 0. Net delta
+10 (vs spec floor of +6). No pytest or Vitest regression. No constraint
violation. Migration call site at `argus/strategies/telemetry_store.py:138`
is byte-for-byte unchanged (`await apply_migrations(self._conn,
schema_name=SCHEMA_NAME, migrations=MIGRATIONS)`).

## 2. Session-specific review focus — line-by-line verification

**(1) Phase A evidence is concrete.**

`grep -E "rowcount_before_commit|rowcount_after_commit|rows_actually_deleted"
dev-logs/2026-04-28_retention-mechanism-diagnostic.md` returns 8 raw-evidence
hits including:

```
rowcount_before_commit                 = 100
rowcount_after_commit                  = 100
rows_actually_deleted                  = 100
```

and the corresponding zero-deletion scenario lines. The diagnostic file is
not a "we believe H1" hand-wave — it is structured raw output from a real
isolation script run, plus a synthesis section that explicitly rules out
H1 ("Proof: scenario 1 returned `rowcount_before_commit = 100`,
`rowcount_after_commit = 100`, with 100 rows actually removed from disk")
and confirms H3 with the exact captured-log trace
(`captured_logs = [('WARNING', 'EvaluationEventStore: periodic retention
iteration failed')]`, `info_log_for_deletion_emitted = False`,
`warning_log_emitted = True`,
`cleanup_propagated_exception = 'OSError: ENOSPC: simulated disk pressure
during VACUUM'`). Phase A's halt-or-proceed gate is correctly invoked —
H1 ruled out, H3 confirmed, no HALT required. ✓

**(2) Fix shape matches Phase A finding.**

The Phase A finding was H3 (vacuum-raises-eats-success-INFO), which
required the deletion-INFO to fire BEFORE `await self._vacuum()`.
Verified at `argus/strategies/telemetry_store.py:348-372`:

- Lines 348-361: `if deleted > 0: logger.info("retention deleted %d rows ...")`
  / `else: logger.info("retention scanned (cutoff %s, 0 rows matched)")` —
  deletion-INFO fires here.
- Lines 363-372: `if deleted > 0 and self.VACUUM_AFTER_CLEANUP:
  await self._vacuum() ... logger.info("post-retention VACUUM complete ...")`
  — this is a separate INFO line that fires only if VACUUM succeeds.

The deletion-INFO is correctly BEFORE `await self._vacuum()` (Phase A
H3-correct). The post-VACUUM INFO is a separate log line that does NOT eat
the deletion record if VACUUM raises. ✓

**(3) Regression test actually regresses.**

Mental revert of the deletion-INFO move — putting `logger.info("retention
deleted ...")` back AFTER `await self._vacuum()` — verified against the
new tests:

- `test_retention_logs_success_path` would still PASS under happy-path
  VACUUM because the original code path also logged after VACUUM. The
  closeout (and the test's docstring) is HONEST about this: "Mental
  revert (move the logger.info back to AFTER await self._vacuum()) →
  this test still PASSES under happy-path VACUUM, but the H4 sibling
  guard test_retention_logs_success_even_when_vacuum_fails would fail."
- `test_retention_logs_success_even_when_vacuum_fails` — patches
  `s._vacuum` to raise `OSError("ENOSPC: simulated disk pressure
  during VACUUM")`, asserts `"retention deleted 1 rows"` IS in
  `caplog.records`. With the deletion-INFO AFTER VACUUM, the OSError
  propagates BEFORE the logger.info is reached — message would not be
  captured — TEST FAILS. This is the canonical mechanism-signature
  regression guard for the H3 mechanism. ✓
- `test_retention_logs_zero_deletion_path` — mental revert: delete the
  `else: logger.info(...)` branch in `cleanup_old_events`. The empty-DB
  path would emit no INFO. Test asserts `any("0 rows matched" in m for m
  in msgs)` — TEST FAILS. ✓

The combined `success_path` (happy-path) + `success_even_when_vacuum_fails`
(H3 mechanism guard) + `zero_deletion_path` (G3 zero-branch guard)
provides revert-proof coverage of every observability gap Phase A
identified. ✓

**(4) G4 is non-bypassable (RULE-039).**

Verified:

```
$ grep -nE "skip.headroom|bypass.headroom|--skip-headroom|skip_headroom|bypass_headroom" argus/strategies/telemetry_store.py
(empty)
```

`_vacuum()` at lines 466-486:
- Headroom calculation has no try/except wrapping (`db_size = ...; free_bytes = ...; required = ...`).
- The headroom-failure branch is `if free_bytes < required: logger.warning(...); return` — straight return, no fallback.
- No env var reads (`os.environ`, `os.getenv`).
- No CLI flag (`argparse`, `sys.argv`).
- No config field that bypasses the check (`pre_vacuum_headroom_multiplier` parameterizes the check but does not disable it; range `[1.0, 10.0]`, default 2.0, so even at the floor of 1.0 the check still requires `free_bytes >= db_size`). ✓

**(5) G5 surfaces 4 fields.**

`grep -nE "size_mb|last_retention_run_at_et|last_retention_deleted_count|freelist_pct" argus/api/routes/health.py argus/core/health.py`:

- `argus/api/routes/health.py:37-40`: `EvaluationDbHealth` Pydantic model —
  exactly 4 fields: `size_mb`, `last_retention_run_at_et`,
  `last_retention_deleted_count`, `freelist_pct`. All `| None` per the
  spec (frontend handles null gracefully on fresh boot).
- `argus/core/health.py:1119-1131`: `get_evaluation_db_health()` returns
  exactly 4 keys in both branches (null-defaults branch and registered-
  store branch). ✓

Not 3, not 5. Exactly 4. ✓

**(6) DEC-389 supersedes politely.**

Verified at `docs/decision-log.md` Cross-References cell:

> DEF-197 (IMPROMPTU-10 closure of unbounded-growth surface — DEC-389
> supersedes the implicit policy without invalidating IMPROMPTU-10's
> mechanism; the 4-hour periodic-task pattern is preserved, only cadence +
> threshold defaults change)

And in the Impact cell:

> The existing IMPROMPTU-10 lifecycle pattern (4-hour periodic task + boot
> cleanup + close()-on-cancel) is preserved unchanged; only the cadence +
> threshold defaults are now config-driven.

The narrative explicitly preserves IMPROMPTU-10's mechanism and
articulates DEC-389 as a supersede-not-invalidate of the implicit policy.
DEF-197 is referenced by ID. ✓

**(7) Migration call site is byte-for-byte unchanged.**

Pre-session: `argus/strategies/telemetry_store.py:84` —
```
        await apply_migrations(
            self._conn, schema_name=SCHEMA_NAME, migrations=MIGRATIONS
        )
```

Post-session: `argus/strategies/telemetry_store.py:138` —
```
        await apply_migrations(
            self._conn, schema_name=SCHEMA_NAME, migrations=MIGRATIONS
        )
```

Line number drifted from 84 to 138 because new code (docstring expansion,
class constants migration, new __init__ signature, observability instance
fields) was inserted ABOVE the `initialize()` method. The call itself is
structurally identical — same function, same arguments, same kwargs. ✓

**(8) No silent-default anti-patterns (RULE-042).**

Verified by `git diff 84d072b..HEAD -- <files> | grep -E "^\+" |
grep -E "getattr"` — empty result. None of the new code introduces
`getattr(obj, "field", default)` silent-default patterns.

The dual-source pattern (`self._config.X` for Pydantic source-of-truth,
`self.RETENTION_DAYS` for instance-attr-read in production) is NOT a
silent-default fallback because:

- `__init__` ALWAYS syncs `self.RETENTION_DAYS = self._config.retention_days`
  (no conditional, no try/except, no `or`).
- Production reads `self.RETENTION_DAYS` which always resolves (instance
  attribute set in `__init__`).
- There is no `getattr(self, "RETENTION_DAYS", default)` in the codebase.
- `self._config = config or EvaluationStoreConfig()` is explicit None
  handling, NOT a silent-default fallback (Pydantic guarantees presence
  of all fields with declared defaults).

The closeout's Judgment Call #2 explicitly addresses this and the spec
author authorized this pattern. ✓

## 3. Sprint-level regression checklist

| Check | Result |
|---|---|
| Migration framework path unaffected (`git diff 84d072b..HEAD -- argus/data/migrations/`) | EMPTY ✓ |
| Sprint 31.8 VACUUM tests unmodified (`git diff 84d072b..HEAD -- tests/strategies/test_telemetry_store_vacuum.py`) | EMPTY ✓ |
| IMPROMPTU-10 lifecycle tests structurally preserved | Only ADDITIONS at file end + 1-line monkeypatch surgical adaptation (`EvaluationEventStore` → `s` for monkeypatch target). No structural modification of the existing 3 IMPROMPTU-10 tests' logic. ✓ |
| No sibling SQLite store touched | `git diff 84d072b..HEAD -- argus/intelligence/counterfactual_store.py argus/intelligence/experiments/store.py argus/intelligence/learning/learning_store.py argus/data/vix_data_service.py argus/intelligence/storage.py argus/core/regime_history.py argus/api/routes/alerts.py` is EMPTY. ✓ |
| `workflow/` submodule untouched | `git diff 84d072b..HEAD -- workflow/` is EMPTY. ✓ |
| Full pytest green | `5279 passed, 36 warnings in 70.21s` — exit 0. ✓ |
| Net pytest delta ≥ +6 | tests.new = 10 (8 in `tests/test_telemetry_store.py`, 2 in `tests/api/test_health.py`). ≥6 with margin. ✓ |
| CLAUDE.md DEF table self-consistent | DEF-231/232/233/234 strikethrough RESOLVED-IN-SPRINT (4 rows verified). DEF-235 OPEN-DEFERRED (1 row verified). ✓ |
| DEC-389 well-formed | Indexed at `docs/dec-index.md` (line 521 area, with prior DEC-388). Full entry at `docs/decision-log.md` with all 7 fields (Date, Sessions, Decision, Rationale, Alternatives Considered, Scope, Cross-References, Impact, Status). ✓ |
| Sprint folder structure complete | All 5 expected files present: `sprint-spec.md`, `session-1-prompt.md`, `session-1-closeout.md`, `doc-sync-manifest.md`, `session-1-review.md` (this file). ✓ |

## 4. Sprint-level escalation criteria

| Criterion | Triggered? |
|---|---|
| Phase A diagnostic produces no conclusive root cause; G1 fix shipped on speculation | NO — H1 conclusively ruled out, H3 conclusively confirmed with raw evidence. |
| `argus/data/migrations/evaluation.py` modified in any way | NO — `git diff 84d072b..HEAD -- argus/data/migrations/` is EMPTY. |
| IMPROMPTU-10 lifecycle tests modified beyond the 1-line monkeypatch surgical adaptation | NO — `git log -p 84d072b..HEAD -- tests/test_telemetry_store.py` shows exactly 1 line removed (the `EvaluationEventStore` class-target monkeypatch) and 1 line added (the `s` instance-target replacement) within the existing test function. All other deltas are pure additions at file end. |
| `RETENTION_DAYS` default in code differs from what the YAML config sets | NO — `config/evaluation_store.yaml` sets `retention_days: 2`. `EvaluationStoreConfig.retention_days = Field(default=2, ge=1, le=30)`. `EvaluationEventStore.RETENTION_DAYS: int = 2`. All three values agree. |
| VACUUM pre-headroom check has a bypass flag | NO — verified via grep for skip/bypass patterns. |
| Health subfield writes to a different DB or namespace than `data/evaluation.db` | NO — `register_evaluation_store(store)` registers a single `EvaluationEventStore` instance; `get_evaluation_db_health()` reads only from that instance. |
| More than 8 files modified outside the explicit allow-list | NO — 17 files total, all on the allow-list (12 modified + 5 new; 7 are docs/config/test, 6 are code, 4 are sprint folder). |
| Pytest or Vitest count regresses | NO — pytest +10, Vitest unchanged (913). |
| DEC-389 written but DEF-234 not strikethrough | NO — DEF-234 is strikethrough at CLAUDE.md DEF table. |

## 5. Honest-deviation accounting

The session reports `MINOR_DEVIATIONS` self-assessment. This is appropriate
and honest. The deviations are:

1. **Fix shape adapted from spec's H1-prescribed (rowcount-before-commit)
   to Phase A's H3-correct (deletion-INFO-before-VACUUM).** The spec
   explicitly authorized this contingency: "If Phase A finds a different
   root cause, adapt the fix shape to match; the observability behavior
   is unchanged." Phase A ruled out H1 with concrete `rowcount_before_commit
   = rowcount_after_commit = 100` evidence; the spec's H1 fix would have
   been a no-op on the in-tree aiosqlite version. The H3-correct fix is
   strictly stronger.
2. **IMPROMPTU-10 surgical adaptation targets instance attribute, not
   `_config`.** Spec said `monkeypatch.setattr(s._config,
   "retention_interval_seconds", 0.05)` (or equivalent). Implementation
   used `monkeypatch.setattr(s, "RETENTION_INTERVAL_SECONDS", 0.05)` (the
   instance attribute). Because production reads `self.RETENTION_INTERVAL_SECONDS`
   (instance attr) NOT `self._config.retention_interval_seconds`, the
   instance-attr monkeypatch is what actually drives the periodic-task
   cadence in the test. The spec's prescription would have set the wrong
   attribute. The implementation is semantically correct; the deviation
   is one word (`s` vs `s._config`) and operationally equivalent to the
   original IMPROMPTU-10 test's class-level monkeypatch effect.
3. **Class constants retained as DEPRECATED aliases synchronized from
   `_config` in `__init__`.** This is the spec's explicit "Keep the
   class constants as DEPRECATED aliases" pattern, realized via instance-
   attribute sync rather than property descriptors. The Sprint 31.8 VACUUM
   regression tests at `tests/strategies/test_telemetry_store_vacuum.py`
   monkeypatch instance attributes; production reads instance attributes;
   `__init__` is the single source-of-truth synchronization point.

All three are documented in the closeout's Judgment Calls section and are
within the spec's authorized contingency envelope.

## 6. Test-strength observation (informational, not a concern)

The new test `test_retention_days_is_config_driven` asserts
`s._config.retention_days == 3` (Pydantic source-of-truth). Production
code reads `s.RETENTION_DAYS` (instance attribute). Both values are equal
after `__init__` (the sync), so the test is correct — but a test that
asserts `s.RETENTION_DAYS == 3` would more directly prove that production
reads the configured value. This is a test-strength observation; the
existing test is not wrong, just not maximally falsifiable. The companion
test `test_retention_logs_success_path` indirectly proves the production
read path via behavioral observation (the cutoff string computed in
`cleanup_old_events()` derives from `self.RETENTION_DAYS`), so coverage
is intact.

This is informational only — does NOT trigger CONCERNS.

## 7. Doc-sync-manifest minor inconsistency (informational, not a concern)

The `doc-sync-manifest.md` says "Header count = 389" in the Files-touched
table for `docs/dec-index.md`. The actual `docs/dec-index.md` header reads
"388 decisions (DEC-001 through DEC-389; DEC-387 freed during Sprint 31.91
planning)" — which is mathematically correct (389 numbers issued − 1
freed = 388 active decisions). The manifest's "Header count = 389" is
sloppy terminology rather than a defect; the actual docs are consistent.

This is informational only — does NOT trigger CONCERNS.

## 8. Architectural soundness

- **Config-gating posture (DEC-032 / `architecture.md` § Config-Gating).**
  `EvaluationStoreConfig` is a Pydantic `BaseModel`, exposed on
  `SystemConfig.evaluation_store` with `default_factory=EvaluationStoreConfig`,
  registered in `_STANDALONE_SYSTEM_OVERLAYS` per DEC-384/FIX-02 standalone-
  overlay convention. Read at runtime via `self._config.<field>` not direct
  YAML access. Idiomatic. ✓
- **Non-bypassable validation (RULE-039 / `architecture.md` § Non-Bypassable
  Validation).** Pre-VACUUM headroom check has no flag, no env var, no
  try/except swallow. Mirrors the Sprint 31.85 Parquet consolidation
  precedent. ✓
- **Fire-and-forget writes (DEC-345 / `architecture.md` § Fire-and-Forget
  Writes).** Periodic retention task uses fire-and-forget pattern via
  `asyncio.create_task`; the broad `except Exception:` in
  `_run_periodic_retention` (preserved unchanged) catches and logs at
  WARNING — IMPROMPTU-10's pattern. The G1 fix specifically addresses
  the silent-failure mode of this exact pattern by emitting the
  observability-critical INFO BEFORE the failure surface (VACUUM). ✓
- **Domain modeling.** New `EvaluationDbHealth` Pydantic model with all
  4 nullable fields. `register_evaluation_store(store)` is a clean
  dependency injection. `get_evaluation_db_health()` correctly handles
  the unregistered case (test fixtures, boot race) with all-null
  defaults. `EvaluationEventStore` imported under `TYPE_CHECKING` in
  `argus/core/health.py:48` to avoid circular imports. ✓

## 9. Closing note

This session is a model implementation of the "Phase A diagnostic informs
Phase B implementation" pattern described in the sprint spec. The
implementer correctly:

1. Wrote a focused isolation diagnostic (deleted post-Phase-A per spec
   A4) with structured raw evidence rather than narrative claims.
2. Conclusively ruled out the spec's primary hypothesis (H1) and
   confirmed an alternative (H3) with falsifiable evidence.
3. Adapted the fix shape to match the confirmed mechanism, with full
   audit trail (closeout Judgment Calls #1).
4. Added a regression test that captures the H3 mechanism specifically
   (`test_retention_logs_success_even_when_vacuum_fails`), not just the
   happy-path observability.
5. Caught and fixed a mid-session regression (the `EvaluationStoreConfig`
   placement orphaning `HealthConfig.alert_webhook_url` `@property`)
   surfaced by full-suite run, BEFORE closeout.
6. Filed DEF-235 honestly as OPEN-DEFERRED rather than expanding scope
   to fix it in-session.

The session's `MINOR_DEVIATIONS` self-assessment is calibrated correctly
— the deviations are real and named, but every one is within the spec's
authorized contingency envelope and is the technically correct choice.

---

## ---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "reviewer_pass_count": 8,
  "concerns": [],
  "informational_observations": [
    "test_retention_days_is_config_driven asserts s._config.retention_days rather than s.RETENTION_DAYS (the instance attribute production reads); both are equal after __init__ so the test is correct, but a stronger version would assert the production read path directly. Not a defect.",
    "doc-sync-manifest.md says 'Header count = 389' for dec-index.md; the actual file's header reads '388 decisions (DEC-001 through DEC-389; DEC-387 freed)' which is mathematically correct (389 issued − 1 freed = 388 active). Manifest text is sloppy but the actual file is consistent. Not a defect."
  ],
  "recommended_next_action": "Operator runs the closeout's CI verification step (DEC-328 / RULE-050), records the green CI URL in the closeout's `ci_run_url` field (currently TBD), then operator restarts ARGUS to activate the new RETENTION_DAYS=2 + pre-VACUUM-headroom-check + /health.evaluation_db subfields.",
  "tests_pass_count": 5279,
  "tests_baseline": 5269,
  "tests_delta": 10,
  "vitest_baseline": 913,
  "vitest_total": 913,
  "files_modified_count": 12,
  "files_new_count": 5,
  "files_total_touched": 17,
  "constraint_violations": 0,
  "phase_a_evidence_concrete": true,
  "fix_shape_matches_phase_a": true,
  "regression_tests_revert_proof": true,
  "g4_non_bypassable": true,
  "g5_field_count": 4,
  "dec_389_supersedes_politely": true,
  "migration_call_site_unchanged": true,
  "no_silent_default_antipatterns": true,
  "sibling_stores_untouched": true,
  "workflow_submodule_untouched": true,
  "impromptu_10_tests_preserved": true,
  "sprint_31_8_vacuum_tests_unmodified": true,
  "self_assessment_calibrated": "MINOR_DEVIATIONS — calibrated correctly; deviations are within spec's authorized contingency envelope",
  "review_focus_results": {
    "1_phase_a_evidence_concrete": "PASS",
    "2_fix_shape_matches_phase_a": "PASS",
    "3_regression_test_actually_regresses": "PASS",
    "4_g4_non_bypassable_rule_039": "PASS",
    "5_g5_surfaces_4_fields": "PASS",
    "6_dec_389_supersedes_politely": "PASS",
    "7_migration_call_site_unchanged": "PASS",
    "8_no_silent_default_antipatterns": "PASS"
  },
  "escalation_criteria_triggered": []
}
```
