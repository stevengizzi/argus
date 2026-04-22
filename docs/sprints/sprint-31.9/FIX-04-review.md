---BEGIN-REVIEW---

# Tier 2 Review — FIX-04-execution

- **Sprint:** audit-2026-04-21-phase-3 (Sprint 31.9)
- **Session:** FIX-04-execution (Wave 2 Rule-4 serial, execution layer)
- **Date:** 2026-04-22
- **Commit reviewed:** `b2c55e5`
- **Baseline HEAD:** `942cf05`
- **Verdict:** **CLEAR**

## Verification Performed

### 1. CRITICAL findings — landed correctly with gold-standard proof

- Grep `argus/execution/**` for `avg_entry_price`: **zero hits in order_manager.py, zero hits in test_order_manager.py, one hit at `alpaca_broker.py:610`** — that hit reads off an alpaca-py SDK `Position` (not the internal `argus.models.trading.Position`) and is CORRECT. Matches the expected post-fix state exactly.
- Grep `argus/execution/order_manager.py` for `getattr(order, "qty"`: **zero hits** (confirmed).
- Three regression tests at `tests/execution/test_order_manager.py:4328/4383/4426` construct real `Position` / `Order` Pydantic models (not `MagicMock`), so field names are enforced by contract. If a future edit re-introduces `avg_entry_price` or `qty`, the Pydantic model's field-name contract will force the `getattr(..., default)` path and the tests will fail.
- **Gold-standard revert proof executed:**
  1. Temporarily reverted the three sites in `order_manager.py` (lines 2044, 2079, 2101).
  2. Ran the three regression tests: `3 failed, 83 deselected in 0.17s` — all three failed with the expected assertion messages (`entry_price=0.0`, `t1_shares=0 ≠ 50`, etc.).
  3. Restored via `git checkout argus/execution/order_manager.py`.
  4. Re-ran the three regression tests: `3 passed, 83 deselected in 0.05s`.
  The regression guards are NOT vacuous.

### 2. Test-count regression guard

- Ran `python -m pytest --ignore=tests/test_main.py -n auto --tb=no -q`: **4,985 passed, 0 failed, 42 warnings, 68.95s**.
- DEF-150 flake did not fire this run (ran outside HH:00/HH:01 window). No DEF-163 / DEF-171 failures either.
- Matches close-out's claimed final count of 4,985 exactly.

### 3. Scope boundary

- `git diff --name-only 942cf05..b2c55e5` produces exactly the 12 files declared as expected in the kickoff. **Zero deviations.** The two acknowledged scope expansions (`ibkr_errors.py`, `tests/execution/test_ibkr_broker.py`) sit inside `argus/execution/` and are load-bearing for the M-05 fall-through fix (without adding 404 to `_ORDER_REJECTION_CODES`, removing the early return alone would NOT trigger `OrderCancelledEvent` publish). Both expansions are documented in close-out judgment call #5 and in the audit resolution section.

### 4. Strikethrough preservation

- `CLAUDE.md:395` — `| ~~DEF-172~~ | ~~Duplicate CatalystStorage ...~~ |` — still struck through, **RESOLVED-VERIFIED** annotation intact.
- `CLAUDE.md:396` — `| ~~DEF-173~~ | ~~LearningStore.enforce_retention() ...~~ |` — still struck through, **RESOLVED** annotation intact.
- `CLAUDE.md:397` — `| DEF-175 | Component ownership consolidation ... |` — live, no strikethrough, pointer to discovery doc preserved. Correct.

### 5. MEDIUM spot-checks

- **M01 (bracket rollback):** `ibkr_broker.py:730` — try/except wraps every leg-build AFTER `parent_trade = self._ib.placeOrder(contract, parent)` at line 717. Except branch at line 783 calls `self._ib.cancelOrder(parent_trade.order)` then re-raises. Docstring at lines 681-682 explicitly softens "atomic" to "rollback-protected but NOT truly atomic in a distributed-systems sense". Correctly implemented.
- **M02 (drain bracket cancel):** `_cancel_open_orders_for_symbol` helper at `order_manager.py:1957`. Called from `_flatten_unknown_position` (line 1933) and `_drain_startup_flatten_queue` (line 2010). Regression test `test_drain_startup_flatten_queue_cancels_brackets_first` at line 4480 seeds the queue, provides a residual stop, and asserts both that `"residual-stop-1" in cancelled` and that `cancel_order` fires during the drain. Ordering is enforced by source structure (cancel at 1933 precedes place at 1943). Adequate.
- **M05 (404 fall-through):** `ibkr_broker.py:367` — `if error_code == 404:` block logs and the `return` is removed; execution continues to `is_order_rejection` check at line 385. `ibkr_errors.py:242` — `_ORDER_REJECTION_CODES = frozenset({110, 200, 201, 203, 404})` with comment at line 238-241 citing FIX-04 P1-C1-M05 rationale. Both ends of the fix present — essential for `OrderCancelledEvent` publish to actually fire on 404.
- **M06 (entry_time bias):** `order_manager.py:2113` — `reconstructed_entry_time = self._clock.now() - timedelta(minutes=self._config.max_position_duration_minutes // 2)` passed as `entry_time=reconstructed_entry_time` at line 2120. Comment explains the stopgap posture and cites DEF-176-style future work ("durable fix ... out of scope"). +1 regression test at line 4542.

### 6. Audit back-annotation completeness

- `docs/audits/audit-2026-04-21/phase-2-review.csv`: exactly **19 rows** contain `FIX-04-execution`. Disposition breakdown: 12 RESOLVED + 2 DEFERRED + (partial/resolved-verified variants).
- `docs/audits/audit-2026-04-21/p1-c1-execution.md:287` — `## FIX-04 Resolution (2026-04-22)` section with per-finding disposition table covering C-01, C-02, M-01, M-02, M-04, M-05, M-06, cross-domain P1-D1-M03, all L-01 through L-10, and P1-G2-M04. Includes test delta, new DEFs, and explicit scope-expansion disclosure.

### 7. DEF accuracy

- **DEF-176** (`CLAUDE.md:399`): concrete migration recipe for removing `auto_cleanup_orphans` kwarg — lists the three reconciliation test modules still using it, specifies the exact deletions in `OrderManager.__init__` (parameter, docstring entry, warnings-guard, fallback). LOW priority. Not a stub.
- **DEF-177** (`CLAUDE.md:400`): concrete 4-step migration for `RejectionStage.MARGIN_CIRCUIT` — (1) extend enum, (2) confirm `main.py:1833` StrEnum parse, (3) bump `order_manager.py:485`, (4) add regression test. MEDIUM priority with operational-signal rationale. Not a stub.

## Findings Summary

**All gates passed with no concerns:**

- Both CRITICALs (C-01, C-02) landed with regression tests that provably fail when the fix is reverted — gold-standard proof executed in my sandbox and verified.
- Test count regression guard: 4,985 passed, 0 failed, matches close-out claim exactly.
- Scope boundary: zero deviations from the declared 12-file set.
- Strikethrough state for DEF-172/173/175 preserved correctly.
- All four MEDIUM spot-checks verified in source (M-01 M-02 M-05 M-06).
- Audit back-annotation is complete (19 CSV rows + full resolution section).
- Both new DEFs have concrete next-step guidance, not TBD stubs.

**Judgment calls reviewed and found reasonable:**

1. Keeping `getattr(default)` pattern over direct attribute access — justified by surrounding code consistency (8+ other getattr calls in the same block). The regression tests guard the field names regardless of access style.
2. Stopgap entry_time bias vs durable sidecar — durable fix requires DB schema change, legitimately out of scope for a Rule-4 serial session. Documented with the correct halt semantics.
3. DeprecationWarning + DEF-176 rather than in-session removal — the three dependent test modules are outside FIX-04's declared scope (reconciliation_* and sprint2875 test files). Honest MINOR_DEVIATIONS self-assessment.
4. Cross-domain P1-D1-M03 deferred to DEF-177 — halt-rule-4 correctly invoked on the `argus/intelligence/` boundary; the execution-side rejection_stage literal would have to change in lock-step with the enum and intelligence-side parse.
5. Extending M-05 to include `_ORDER_REJECTION_CODES` edit — correct diagnosis. Without this, the surface-level "remove early return" alone would have failed silently (404 would not be recognized by `is_order_rejection`, no `OrderCancelledEvent` would publish). The scope expansion into `ibkr_errors.py` is load-bearing, not gratuitous.
6. Broker router deletion without `docs/architecture.md` update — reasonable deferral to DEF-168 (existing API-catalog drift DEF).
7. `eod_flatten_timeout_seconds=1` over `0.1` — forced by Pydantic `ge=1` validator; operationally equivalent for the test purpose.

**Minor observations (not defects, not CONCERNS-worthy):**

- The M-02 regression test asserts cancel fires during the drain but does not strictly interleave call-order assertions (it counts calls). The source-level ordering is unambiguous (cancel at line 1933 before place at 1943), so this is adequate. A stricter version could use a shared call-sequence recorder. Informational only.
- Close-out's "Deferred observations" item (2) — `alpaca_broker.py:610` using `pos.avg_entry_price` — was independently verified during this review and is correct (SDK object, not internal model).

## Escalation Criteria Check

None triggered:

- Regression tests DO fail when fix is reverted (verified in sandbox).
- Pytest net delta is +1 (≥ 0 gate satisfied).
- No scope boundary violations (exact expected file set).
- No failures outside the DEF-150/163/171 flake set.
- Only the authorized Rule-4 file (`order_manager.py`) was touched at the sensitive level.
- Audit back-annotation is present and materially correct.
- DEF-172/173 strikethrough preserved; DEF-175 not accidentally struck.

## Verdict: CLEAR

FIX-04 executed cleanly on the highest-risk file in the codebase. The CRITICAL regression guards are real (verified by revert-and-fail proof), the scope held within the declared boundary, and the two deferred findings (L-10 → DEF-176, P1-D1-M03 → DEF-177) are correctly out-of-scope for a Rule-4 serial session with concrete next-step recipes recorded. The MINOR_DEVIATIONS self-assessment in the close-out is accurate and conservative — I would have been comfortable seeing it as CLEAN given that both scope expansions were load-bearing and inside `argus/execution/`, but the implementer's more conservative framing is commendable.

```json:structured-verdict
{
  "session_id": "FIX-04-execution",
  "sprint_id": "audit-2026-04-21-phase-3",
  "commit_sha": "b2c55e5",
  "baseline_head": "942cf05",
  "verdict": "CLEAR",
  "review_date": "2026-04-22",
  "reviewer": "Tier 2 automated reviewer",
  "test_count_verified": 4985,
  "test_count_net_delta": 1,
  "critical_regression_revert_proof_executed": true,
  "critical_regression_revert_proof_result": "3 tests failed on revert, 3 passed on restore",
  "scope_boundary_violations": [],
  "files_modified_count": 12,
  "files_modified_expected": 12,
  "findings_back_annotated_csv": 19,
  "findings_back_annotated_expected": 19,
  "resolution_section_present": true,
  "def_172_strikethrough_preserved": true,
  "def_173_strikethrough_preserved": true,
  "def_175_live_preserved": true,
  "def_176_has_concrete_guidance": true,
  "def_177_has_concrete_guidance": true,
  "medium_spotchecks_passed": ["P1-C1-M01", "P1-C1-M02", "P1-C1-M05", "P1-C1-M06"],
  "escalation_criteria_triggered": [],
  "concerns": [],
  "observations": [
    "M-02 regression test counts cancel/place calls rather than asserting strict call-order interleaving; source-level ordering is unambiguous so this is adequate but could be made stricter in a future pass",
    "alpaca_broker.py:610 correctly uses pos.avg_entry_price (SDK object, not internal model) — verified independently"
  ],
  "judgment_calls_reviewed_and_approved": [
    "getattr(default) pattern kept for internal consistency; regression tests guard field names regardless",
    "stopgap entry_time bias (M-06) over durable sidecar persistence — correct halt on schema-change scope",
    "DeprecationWarning over in-session removal (L-10) — three dependent test modules outside declared scope",
    "P1-D1-M03 deferred to DEF-177 — halt-rule-4 correctly invoked on intelligence/ boundary",
    "M-05 extended to include ibkr_errors.py _ORDER_REJECTION_CODES — load-bearing for OrderCancelledEvent publish",
    "broker_router deletion without architecture.md update — tracked under DEF-168",
    "eod_flatten_timeout_seconds=1 (Pydantic ge=1 minimum)"
  ]
}
```

---END-REVIEW---
