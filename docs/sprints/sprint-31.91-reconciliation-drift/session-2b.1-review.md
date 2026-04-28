# Sprint 31.91, Session 2b.1 — Tier 2 Review

> **Scope:** Broker-orphan branch + alert taxonomy (`phantom_short` CRITICAL on broker-orphan SHORT; `stranded_broker_long` WARNING with M2 exp-backoff on broker-orphan LONG cycle ≥3) + per-symbol consecutive-cycle counter infrastructure with cleanup-on-zero + session-reset.
> **Reviewer:** Tier 2 backend safety reviewer (read-only).
> **Anchor:** Working tree on `main` over predecessor commit `682b7ff` (Session 2a + work-journal register refresh). Session 2b.1 is uncommitted; Tier 2 verdict gates the commit per the sprint's review-before-commit policy (consistent with 2a).
> **Date:** 2026-04-27.

---BEGIN-REVIEW---

## Verdict — CLEAR

Session 2b.1 is a structurally clean detection-layer addition. The new broker-orphan branch attaches cleanly to `OrderManager.reconcile_positions` *after* the existing ARGUS-orphan branch, iterates a different surface (`broker_positions.items()` rather than the existing `discrepancies` list), and is mechanically incapable of overlapping with the ARGUS-orphan branch by the algebraic conditions on internal vs broker quantities. DEC-369/DEC-370 broker-confirmed immunity is preserved by construction — the explicit `if symbol in self._managed_positions: continue` guard filters out every broker-confirmed position before any side dispatch. The two new alert handlers gate at entry on `broker_orphan_alert_enabled`, populate `metadata` structurally with `symbol`/`shares`/`side`/`detection_source` so HealthMonitor (5a.1) can cross-reference by typed key, and emit log lines that the regression-protection tests assert on exact substrings. The exponential-backoff schedule walks through cleanly — `last_alerted` only ever takes a value FROM the schedule (during the schedule phase) or a post-48 cap value, so the "in-between" misfire question raised in Focus item 3 is structurally unreachable. No do-not-modify-list file is touched. No Session 2c.1 gate state is introduced. The `SystemAlertEvent.metadata` schema extension is exactly what Session 5a.1's Pre-Flight Check 7 explicitly accommodates ("If the field IS present, skip Requirement 0"), so 5a.1's atomic-migration scope for the two pre-existing emitters is unchanged. Test count 5,133 → 5,139 (+6, exactly matching new tests added). `tests/test_main.py` baseline holds at 39 pass + 5 skip. Scoped suite green at 468.

## Assessment Summary

| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All eight requirements landed; no scope creep. SystemAlertEvent.metadata addition is explicitly accommodated by 5a.1's Pre-Flight 7. |
| Close-Out Accuracy | PASS | Diff stats match (7 modified + 1 untracked test file = 8 file deltas). Test counts match (462→468 scoped, 5,133→5,139 full). |
| Test Health | PASS | All 6 new tests pass in isolation; 468 passing scoped; 5,139 passing full. |
| Regression Checklist | PASS | Invariants 1, 2, 5, 6, 8, 13, 14, 15 verified; 3, 4, 7, 9, 10, 11, 12 not in scope or unaffected. |
| Architectural Compliance | PASS | Branch ordering, gate placement, metadata shape, M2 lifecycle all match spec. |
| Escalation Criteria | NONE_TRIGGERED | A1 fires post-Session-1c (already complete); A2 not triggered (verdict CLEAR); B-class halts not triggered. |

## Review-Focus Findings

### 1. Alert payload shape correctness (Focus item 1)

**PASS.** Verified directly against `argus/core/events.py:405-432`:

- Existing `SystemAlertEvent` fields (`source`, `alert_type`, `message`, `severity`) all populated correctly by both new emitters.
- `severity="critical"` for `phantom_short` (matches DEF-204 detection-signal semantics; CRITICAL log line also fires).
- `severity="warning"` for `stranded_broker_long` (matches spec D5 — long orphan is non-emergency).
- `source="reconciliation"` on both (per spec D5 §"Detection + alerts (2b.1)").
- `alert_type` strings match spec exactly: `"phantom_short"` and `"stranded_broker_long"`.

**Schema extension audit (DEF-213 partial).** The `metadata: dict[str, Any] | None = None` addition to `SystemAlertEvent` is the same shape as Session 5a.1's Pre-Flight Check 7 expects:

> Lines 51-67 of `sprint-31.91-session-5a.1-impl.md`:
> > "If `metadata: dict[str, Any] | None` is NOT present in `SystemAlertEvent`, do Requirement 0 (below) BEFORE proceeding to any other requirement. **If the field IS present (i.e., a prior session added it), skip Requirement 0 and proceed to Requirement 1.**"

5a.1's atomic-migration scope for the two pre-existing emitters (Databento dead-feed at `databento_data_service.py:279` and `_emit_cancel_propagation_timeout_alert` at `order_manager.py:2163`) is preserved unchanged — the metadata field is now present, but those emitters still need to be migrated to populate it structurally. 2b.1 emits `phantom_short` / `stranded_broker_long` populated from day one. **No semantic conflict with 5a.1's atomic-migration intent; no scope creep.**

### 2. Cycle counter resets on broker-zero (Focus item 2)

**PASS.** Verified by reading `order_manager.py:3683-3696` (the cleanup loop):

```python
resolved_symbols = (
    set(self._broker_orphan_long_cycles.keys())
    - set(broker_positions.keys())
)
for symbol in resolved_symbols:
    self._broker_orphan_long_cycles.pop(symbol, None)
    self._broker_orphan_last_alerted_cycle.pop(symbol, None)
    logger.info(...)
```

The cleanup loop is INSIDE `reconcile_positions`, AFTER the broker-orphan branch, BEFORE the `_last_reconciliation` write. It runs unconditionally on every reconciliation cycle. Test 6 sub-behavior A verifies the counter clears after broker-zero observation; the `assert "AAPL" not in om._broker_orphan_long_cycles` assertion at line 368 of the test catches any revert.

### 3. Exponential backoff calculation (Focus item 3)

**PASS.** Walked through manually:

- cycle=3, last_alerted=0: `should_alert = (cycle == 3)` → True. last_alerted ← 3.
- cycles 4-5: next_in_schedule = 6, cycle < 6 → False.
- cycle=6: cycle ≥ 6 → True. last_alerted ← 6.
- cycles 7-11: next_in_schedule = 12, cycle < 12 → False.
- cycle=12: True. last_alerted ← 12.
- ... cycle=48: True. last_alerted ← 48.
- cycle=49: `next_in_schedule = next(c for c in [3,6,12,24,48] if c > 48)` = `None` → falls into the hourly cap branch: `(49 - 48) >= 60` = False.
- cycle=108: `(108 - 48) = 60 >= 60` → True. last_alerted ← 108.
- cycle=168: `(168 - 108) = 60 >= 60` → True.

**The "last_alerted between schedule entries" concern is structurally unreachable.** `last_alerted` is only ever set when `should_alert` is True, and `should_alert` is True only at exact schedule values during the schedule phase (3, 6, 12, 24, 48). After 48, `last_alerted` advances by exactly 60-cycle increments. So `last_alerted ∈ {0, 3, 6, 12, 24, 48, 108, 168, ...}` — never an "in-between" value. The `next()` lookup with `if c > last_alerted` is therefore always well-defined.

Test 6 sub-behavior B confirms the schedule empirically by running 50 cycles and asserting `fired_cycles == {3, 6, 12, 24, 48}` exactly — no spurious fires at any of cycles 4, 5, 7-11, 13-23, 25-47, 49-50.

### 4. Session reset clears stale state (Focus item 4)

**PASS.** Verified at `order_manager.py:3411-3413`:

```python
self._broker_orphan_long_cycles.clear()
self._broker_orphan_last_alerted_cycle.clear()
```

These two lines are inside `reset_daily_state()` (the existing session-start hook ARGUS already wires for ResetDailyEvent / SessionStartEvent dispatch). Test 6 sub-behavior C sets up TSLA at cycle 5 with last_alerted=3, calls `om.reset_daily_state()`, asserts both dicts are empty, and re-runs cycles 1-3 to verify the alert re-fires from a clean slate. The new state fields are now part of the existing canonical reset surface.

### 5. DEC-369 / DEC-370 immunity preserved (Focus item 5)

**PASS.** Two layers of defense, both verified:

1. **The `if symbol in self._managed_positions: continue` guard at the top of the broker-orphan loop body** (`order_manager.py:3657-3658`). Broker-confirmed positions live in `_managed_positions` (set at entry-fill time at `:1108` and never removed except on close at `:3343` or session reset at `:3394`). The guard filters them BEFORE any side dispatch, so they never enter `_handle_broker_orphan_short` or `_handle_broker_orphan_long`.
2. **The existing ARGUS-orphan branch at `:3571` and broker-confirmed branch at `:3576-3587` are wholly unchanged** by the diff. The pre-existing immunity test `test_confirmed_position_not_cleaned_on_snapshot_miss` passes green on the patched code (verified during this review).

The 23 pre-existing reconciliation tests under `tests/execution/order_manager/test_reconciliation*.py` all pass green post-patch.

### 6. Config gate works at BOTH handlers (Focus item 6)

**PASS.** Verified by reading the function bodies:

- `_handle_broker_orphan_short` (`:2213-2214`):
  ```python
  if not self._reconciliation_config.broker_orphan_alert_enabled:
      return  # config-gated; allow operator to disable for testing
  ```
  This is the FIRST line of the function body, before the CRITICAL log AND before the `SystemAlertEvent.publish()`.

- `_handle_broker_orphan_long` (`:2266-2267`):
  ```python
  if not self._reconciliation_config.broker_orphan_alert_enabled:
      return
  ```
  Same pattern: first line of the body, before the cycle <3 WARNING log AND before any alert publish.

Test 3 (`test_broker_orphan_alert_config_flag_disables`) verifies BOTH the alert event suppression AND the CRITICAL log suppression for the SHORT path. Symmetric coverage for the LONG-cycle-3 path is implicit: if the gate is at function entry, both early-return paths are equivalently protected. The test's strength is enough — a regression that moves the gate past one of the side-effect lines would fail the existing assertion (`assert critical_lines == []`).

### 7. No coupling to Session 2c.1's gate state (Focus item 7)

**PASS.** Verified by full-tree grep:

```bash
$ grep -rn "phantom_short_gate\|gated_symbols\|phantom_short_entry_gate" argus/ tests/
(empty)
```

The 2b.1 diff introduces NO `_phantom_short_gated_symbols`, NO `phantom_short_gate_state`, NO new entry-rejection branch. The detection-without-blocking interim state is correctly enforced by the spec D5 §"Detection + alerts (2b.1)" boundary.

### 8. HealthMonitor cross-reference (Focus item 8)

**PASS.** Both alert types populate `metadata["symbol"]`:

- `_handle_broker_orphan_short` (`:2244-2249`):
  ```python
  metadata={
      "symbol": symbol,
      "shares": recon_pos.shares,
      "side": "SELL",
      "detection_source": "reconciliation.broker_orphan_branch",
  },
  ```
- `_handle_broker_orphan_long` (`:2329-2335`):
  ```python
  metadata={
      "symbol": symbol,
      "shares": recon_pos.shares,
      "side": "BUY",
      "consecutive_cycles": cycle,
      "detection_source": "reconciliation.broker_orphan_branch",
  },
  ```

HealthMonitor (5a.1) can build a per-symbol active-alert index by reading `event.metadata["symbol"]`. The `stranded_broker_long` alert additionally carries `consecutive_cycles` so 5a.2's auto-resolution policy table can compute "5 cycles zero-shares" / "broker reports zero" thresholds against typed metadata. Tests 2 and 5 lock in the metadata shape.

## Sprint-Level Regression Checklist

| # | Invariant | Result | Notes |
|---|---|---|---|
| 1 | DEF-199 A1 fix detects + refuses 100% of phantom shorts at EOD | PASS | `git diff HEAD --` on `order_manager.py` shows hunks at `:361`, `:2185`, `:3261`, `:3490` — none overlap `:1670-1750`. |
| 2 | DEF-199 A1 EOD Pass 1 retry still respects side check | PASS | Same audit. |
| 3 | DEF-158 dup-SELL prevention works for ARGUS=N, IBKR=N | N/A | Session 3 territory. |
| 4 | DEC-117 atomic bracket invariant preserved | N/A | Session 1a territory; sealed in Tier 3 review #1. |
| 5 | Existing 5,080 pytest baseline holds | PASS | 5,139 (+59 above floor; +6 from 2a's 5,133). |
| 6 | `tests/test_main.py` baseline holds (39 pass + 5 skip) | PASS | Verified locally: 39 passed, 5 skipped. |
| 7 | Vitest baseline holds at 866 | N/A | Backend session; no frontend changes. |
| 8 | Risk Manager check 0 unchanged | PASS | `git diff HEAD --stat -- argus/core/risk_manager.py` empty. |
| 9 | IMPROMPTU-04 startup invariant unchanged | PASS | `git diff HEAD --stat -- argus/main.py` empty. |
| 10 | DEC-367 margin circuit breaker unchanged | PASS | No edits to circuit-breaker code. |
| 11 | Sprint 29.5 EOD flatten circuit breaker unchanged | PASS | Same. |
| 12 | Pre-existing flakes did not regress | PASS | Full suite green; pre-existing flake list unchanged. CI not yet run on the unsubmitted commit (RULE-050 caveat below). |
| 13 | New config fields parse without warnings | PASS | `python -c "...SystemConfig..."` → both YAMLs parse with `broker_orphan_alert_enabled=True`. |
| 14 | Monotonic-safety property holds at session merge | PASS | Row "After Session 2b.1": Recon detects shorts = "partial (alert only)". Verified — no gate engagement, no count-filter changes. |
| 15 | No items on the do-not-modify list were touched | PASS | All eight protected paths verified clean via `git diff HEAD --stat`. |
| 16 | Bracket placement performance does not regress | N/A | Session 4 territory. |
| 17 | Mass-balance assertion at session debrief | N/A | Session 4 territory. |
| 18-22 | Alert observability invariants | N/A | Sessions 5a.1+ territory. |

## Architectural Compliance

- **Domain model (DEF-139/140 `shares` vs `qty`):** New code reads `recon_pos.shares` only; never `getattr(..., "qty", 0)`. Compliant.
- **Frozen dataclass (`ReconciliationPosition`):** Inputs are typed; defensive `else: logger.error` branch guards against future caller drift but is unreachable in current code (post_init rejects None side).
- **EventBus async-via-`asyncio.create_task` (architecture.md async discipline):** New emitters use `await self._event_bus.publish(...)` (no fire-and-forget; the publish is awaited). The `try/except logger.exception` wrapper is defensive against subscriber-handler exceptions but doesn't suppress propagation of the publish itself; appropriate.
- **Config-gated (DEC-032, code-style.md §Config-Gating):** New `broker_orphan_alert_enabled: bool = True` lives on `ReconciliationConfig` (existing Pydantic submodel on `SystemConfig`); read via `self._reconciliation_config.broker_orphan_alert_enabled`. No direct `yaml.safe_load` in the feature module. Compliant.
- **ThrottledLogger (Sprint 27.75, DEC-363):** The cycle ≥3 path uses the M2 exp-backoff schedule as the throttle (3 → 6 → 12 → 24 → 48 → every 60). The cycle 1-2 WARNING log is unthrottled but bounded — at most 2 WARNINGs per orphan symbol, and the orphan resolves on broker-zero or persists into the cycle ≥3 schedule. Acceptable.
- **Test discipline (testing.md):** New tests follow function-style naming, use `_capture_alerts` + `_reconcile_and_drain` helpers (mirroring `test_broker_only_paths_safety.py` conventions), and assert on exact metadata keys + log substrings — revert-proof.
- **Universal RULE-038 (grep-verify):** Implementer's docstring at `:3649-3654` notes "broker-confirmed positions are never in this branch by construction" — claim grep-verified during this review.
- **Universal RULE-050 (CI green on final commit):** Session 2b.1 is uncommitted. CI is green on the predecessor commit (`682b7ff`, run `25030315564`). The sprint's "Tier 2 verdict gates the commit" pattern (consistent with 2a) means CI verification on 2b.1's actual final commit happens AFTER this review. Documented as a procedural note, not a finding.

## Findings

(No HIGH or CRITICAL findings. No CONCERNS-grade findings. The review is CLEAR.)

### Informational notes (not findings)

- **`SystemAlertEvent.metadata` field naming.** Session 5a.1's Pre-Flight 7 explicitly accommodates "field already present" by skipping Requirement 0; the implementer made the right call by adding the field with the exact shape 5a.1 expects (`dict[str, Any] | None = None`). This avoids a delta cliff at 5a.1 where every subsequent emitter would have referenced a non-existent field. The closeout's discussion of this decision at "Discovered Edge Cases #1" is accurate.
- **Defensive `try/except` around `event_bus.publish`.** Both handlers wrap the publish in `try/except Exception` with `logger.exception`. This is defensive against a subscriber raising during dispatch, NOT a suppression of the publish itself. Reasonable; explicitly marked `# pragma: no cover - defensive`.
- **`# type: ignore[arg-type]` audit:** None added by 2b.1.
- **`tests/test_main.py` not exercised by 2b.1's diff.** The closeout correctly notes that `main.py` is untouched; the test_main.py baseline check (39 pass + 5 skip) is the at-maximum-risk invariant for sessions touching `main.py` and is unaffected here. Verified locally regardless.

## Recommendation

**Proceed to commit and next session.** Session 2b.1 lands cleanly. The two remaining structural items (Session 2b.2's side-aware count-filter reads + alert-taxonomy alignment at EOD Pass 2; Session 2c.1's per-symbol entry gate) inherit a working detection-and-alert layer with typed metadata that downstream consumers can read by typed key. The DEF-204 detection signal is now observable; alert-fatigue defense (M2 exp-backoff) is in place; the operator daily `ibkr_close_all_positions.py` mitigation continues to apply per the sprint's standing posture.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "31.91",
  "session": "2b.1",
  "verdict": "CLEAR",
  "findings": [],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All 8 requirements landed: cycle-counter state fields, broker-orphan branch with side dispatch, _handle_broker_orphan_short with phantom_short alert, _handle_broker_orphan_long with M2 exp-backoff (3→6→12→24→48→every 60), counter cleanup on broker-zero, session-reset wiring, broker_orphan_alert_enabled config (default True), DEC-369/DEC-370 immunity preserved by construction. Schema extension to SystemAlertEvent.metadata is explicitly accommodated by Session 5a.1 Pre-Flight 7 ('field already present → skip Requirement 0'); no scope creep into 5a.1's atomic-migration of pre-existing emitters.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/core/events.py",
    "argus/core/config.py",
    "argus/execution/order_manager.py",
    "config/system.yaml",
    "config/system_live.yaml",
    "tests/execution/order_manager/test_session2b1_broker_orphan_alerts.py",
    "tests/execution/order_manager/test_reconciliation_log.py",
    "tests/execution/order_manager/test_reconciliation_redesign.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 5139,
    "new_tests_adequate": true,
    "test_quality_notes": "6 new tests in tests/execution/order_manager/test_session2b1_broker_orphan_alerts.py. Tests are revert-proof: branch ordering (Test 1), alert payload shape (Test 2), config gate (Test 3), cycle 1-2 vs cycle 3 (Tests 4 + 5), M2 lifecycle composite (Test 6 — exhaustively asserts {3, 6, 12, 24, 48} exact-match across 50 cycles, cleanup-on-zero, session-reset). Pre-existing 23 reconciliation tests including DEC-369 immunity test_confirmed_position_not_cleaned_on_snapshot_miss pass green post-patch. Two pre-existing tests minimally updated for additive-change accommodation (test_reconciliation_log.py filter by 'Position reconciliation:' prefix; test_reconciliation_redesign.py expected_keys set extended). Scoped suite 462 → 468 (+6); full suite 5,133 → 5,139 (+6). tests/test_main.py 39 pass + 5 skip baseline holds."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Invariant 1 — DEF-199 A1 fix region untouched", "passed": true, "notes": "Diff hunks at :361, :2185, :3261, :3490; none overlap :1670-1750."},
      {"check": "Invariant 2 — A1 Pass 1 retry side check intact", "passed": true, "notes": "Same audit."},
      {"check": "Invariant 5 — 5,080 pytest baseline holds", "passed": true, "notes": "Local run: 5,139 passed (+6 from 2a's 5,133)."},
      {"check": "Invariant 6 — tests/test_main.py 39 pass + 5 skip", "passed": true, "notes": "Verified locally."},
      {"check": "Invariant 8 — Risk Manager check 0 unchanged", "passed": true, "notes": "Zero edits to argus/core/risk_manager.py."},
      {"check": "Invariant 9 — IMPROMPTU-04 startup invariant unchanged", "passed": true, "notes": "Zero edits to argus/main.py."},
      {"check": "Invariant 13 — new config fields parse cleanly", "passed": true, "notes": "Both system.yaml and system_live.yaml parse with broker_orphan_alert_enabled=True."},
      {"check": "Invariant 14 — Monotonic-safety property", "passed": true, "notes": "Row 'After Session 2b.1' = 'partial (alert only)' per spec; no gate engagement, no count-filter changes."},
      {"check": "Invariant 15 — do-not-modify list untouched", "passed": true, "notes": "All eight protected paths verified clean via git diff."}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Commit Session 2b.1's changes (8-file diff: argus/core/events.py, argus/core/config.py, argus/execution/order_manager.py, config/system.yaml, config/system_live.yaml, tests/execution/order_manager/test_reconciliation_log.py, tests/execution/order_manager/test_reconciliation_redesign.py, tests/execution/order_manager/test_session2b1_broker_orphan_alerts.py) following the sprint's commit convention.",
    "Verify CI green on the final commit (RULE-050) before starting Session 2b.2.",
    "Proceed to Session 2b.2 (side-aware count-filter reads + Pattern B alert-taxonomy alignment at EOD Pass 2)."
  ],
  "donotmodify_violations": 0,
  "tests_total_after": 5139,
  "tier_3_track": "side-aware-reconciliation"
}
```
