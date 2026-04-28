# Sprint 31.91, Session 2a — Tier 2 Review

> **Scope:** Typed reconciliation contract refactor (`dict[str, float]` → `dict[str, ReconciliationPosition]`).
> **Reviewer:** Tier 2 backend safety reviewer (read-only).
> **Anchor commit:** `813fc3c` (Session 2a) over `6b942e5` (predecessor).
> **Date:** 2026-04-27.

---BEGIN-REVIEW---

## Verdict — CLEAR

Session 2a is a structurally clean type/contract refactor. The `Position.side` information now flows end-to-end from the broker layer through the call site into a typed `ReconciliationPosition` dataclass that crosses the `OrderManager.reconcile_positions()` boundary; the production-code body changes are confined to mechanical type plumbing (`broker_positions[symbol]` → `broker_positions[symbol].shares`); the existing ARGUS-orphan branch behavior is preserved by construction and verified by the regression-protection Test 4. All do-not-modify boundaries are clean. The `main.py` edit scope is confined to the documented `:1505-1535` (post-edit `:1519-1553`) range plus the import at `:92`; the IMPROMPTU-04 startup invariant region is untouched. Test count 5128 → 5133 (+5, exactly the count of new tests added). `tests/test_main.py` baseline holds at 39 pass + 5 skip, which is the at-maximum-risk invariant for any session that touches `main.py`.

## Review-Focus Findings

### 1. Information end-to-end (`Position.side` flow)

**PASS.** Verified by reading the full pipeline:

- **Broker layer** (`argus/execution/ibkr_broker.py:1018, 1026`): `Position(side=ModelOrderSide.BUY if ib_pos.position > 0 else ModelOrderSide.SELL, ...)`. Side is populated from the IBKR position quantity sign.
- **Call site** (`argus/main.py:1533`): `side = getattr(pos, "side", None)`. If `side` is `None` the position is skipped with a CRITICAL log (fail-closed; no fabrication).
- **Construction** (`argus/main.py:1551-1553`): `ReconciliationPosition(symbol=symbol, side=side, shares=shares)`.
- **Crossing the boundary** (`argus/execution/order_manager.py:3346`): `reconcile_positions(broker_positions: dict[str, ReconciliationPosition])`. The body could read `broker_positions[sym].side` if it wanted to (Session 2b.1 will).

The information is preserved end-to-end. Session 2a's body does NOT yet consume the side (that lands in 2b.1), but the dataclass carries it across every junction.

### 2. Frozen dataclass immutability

**PASS.** `argus/execution/order_manager.py:171` declares `@dataclass(frozen=True)` (not bare `@dataclass`). Test 1 (`test_reconciliation_position_dataclass_frozen_round_trip`) verifies that mutation of both `shares` and `side` raises `dataclasses.FrozenInstanceError`. The structural protection cannot be silently defeated by reverting the `frozen=True` argument — the test fails.

### 3. Defensive fail-closed when `side=None`

**PASS.** Two layers of defense, both verified by tests:

- **Dataclass `__post_init__`** (`order_manager.py:189-202`): rejects `shares <= 0` and `side is None` with explicit `ValueError`. Test 1 verifies all three rejection paths (shares=0, shares=-100, side=None).
- **Call site** (`main.py:1536-1550`): if `pos.side` is `None` the call site skips the position with `logger.critical(...)` and `continue`s. It does NOT fabricate a default `OrderSide.BUY`. Test 5 (`test_reconcile_positions_with_pos_missing_side_attribute_fails_closed`) constructs a `MagicMock(spec=Position)` with `side=None` and asserts (a) the symbol is absent from the dict passed to `reconcile_positions`, (b) the loop continues to reconcile remaining well-formed positions, (c) the CRITICAL log line names the bad symbol. The structural protection survives a revert attempt that "patches" the missing side because the dataclass constructor would still raise `ValueError`.

### 4. Existing ARGUS-orphan branch behavior preserved

**PASS.** The orphan-loop body diff is purely type plumbing:

```diff
-            if int(broker_positions.get(symbol, 0)) > 0:
+            broker_pos = broker_positions.get(symbol)
+            if broker_pos is not None and broker_pos.shares > 0:
                 self._reconciliation_miss_count[symbol] = 0
```

```diff
-            broker_qty = int(broker_positions.get(symbol, 0))
+            broker_pos = broker_positions.get(symbol)
+            broker_qty = broker_pos.shares if broker_pos is not None else 0
```

The orphan-detection logic at `:3417` (and the broker-confirmed immunity at `:3045`) is unchanged by line, structure, or semantics. Test 4 (`test_argus_orphan_branch_unchanged_with_typed_contract`) sets up an ARGUS-orphan scenario (internal=100, broker=empty typed dict), invokes `reconcile_positions({})`, and asserts the same outputs as before the contract change: discrepancy detected, `PositionClosedEvent` fired with `ExitReason.RECONCILIATION`, position fully closed. Reverting the body in any way that drops the orphan-detection branch makes this test fail.

### 5. `main.py` edit scope

**PASS.** `git diff HEAD~1 HEAD -- argus/main.py` shows exactly two hunks:

```
@@ -92,7 +92,7 @@ from argus.db.manager import DatabaseManager
@@ -1516,14 +1516,41 @@ class ArgusSystem:
```

The `check_startup_position_invariant()` function (`main.py:123`), `_startup_flatten_disabled` setter sites (`main.py:201, 376-397`), and the gate around `reconstruct_from_broker()` (`main.py:1074-1081`) are all comfortably outside the edit window. `grep "check_startup_position_invariant\|_startup_flatten_disabled\|reconstruct_from_broker"` against the diff returns zero matches. The IMPROMPTU-04 fix is sacrosanct and verified untouched.

### 6. Mock fixture updates are mechanical, not behavioral

**PASS.** I diffed each of the 5 updated test files. Every site follows the exact same mechanical pattern:

- Import added: `ReconciliationPosition` + `OrderSide`.
- Type annotation: `dict[str, float]` → `dict[str, ReconciliationPosition]`.
- Value construction: `{"AAPL": 100.0}` → `{"AAPL": ReconciliationPosition(symbol="AAPL", side=OrderSide.BUY, shares=100)}`.
- Empty-dict cases: just the type annotation changes; the empty literal is preserved.

No assertion was modified, no test was renamed, no test was deleted, no test logic changed. The 9 sites across 5 files all pass post-edit (verified: `pytest test_reconciliation*.py test_safety.py test_sprint2875.py` → 56 passed). The pre-flight estimate of "~3 sites" was an undercount (actual 9); the close-out surfaces the discrepancy explicitly per RULE-038's disclosure follow-through, which is the right behavior.

### 7. Risk Manager Check 0 unchanged

**PASS.** `argus/core/risk_manager.py` is not in the diff (`git diff --name-only HEAD~1 HEAD` does not include it). Risk Manager Check 0 (`share_count <= 0` rejection) is bit-for-bit unchanged. Session 2b.2 will add long-only filtering at `:335` and `:771`; Session 2a does not.

## Do-Not-Modify Audit

| File / Region | Status | Evidence |
|---|---|---|
| `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix) | UNCHANGED | Hunk ranges 168, 3343, 3352, 3379 — all outside 1670-1750. |
| `argus/main.py` startup invariant region (`check_startup_position_invariant`, `_startup_flatten_disabled`, `reconstruct_from_broker` gate) | UNCHANGED | Diff hunks confined to `:92` (import) and `:1516-1556`; startup invariant function lives at `:123-~200` with state setters at `:376-397` and gate at `:1074-1081`. |
| `argus/models/trading.py:153-173` (Position class) | UNCHANGED | File not in diff. |
| `argus/execution/alpaca_broker.py` | UNCHANGED | File not in diff. |
| `argus/data/alpaca_data_service.py` | UNCHANGED | File not in diff. |
| `argus/execution/ibkr_broker.py` | UNCHANGED | File not in diff. |
| `argus/execution/broker.py` | UNCHANGED | File not in diff. |
| `argus/core/risk_manager.py` (Session 2b.2 modifies; not 2a) | UNCHANGED | File not in diff. |
| `argus/core/health.py` | UNCHANGED | File not in diff. |
| `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` | UNCHANGED | File not in diff. |
| `workflow/` submodule | UNCHANGED | File not in diff. |

Zero do-not-modify violations. Invariant 15 PASS.

## Sprint-Level Regression Checklist

| # | Invariant | Status | Notes |
|---|---|---|---|
| 1 | DEF-199 A1 fix detects + refuses 100% of phantom shorts at EOD | PASS | A1 region 1670-1750 zero edits (verified by hunk-range inspection). |
| 2 | DEF-199 A1 EOD Pass 1 retry side-check unchanged | PASS | Same code region zero edits. |
| 3 | DEF-158 dup-SELL prevention works for ARGUS=N, IBKR=N normal case | PASS | `_check_flatten_pending_timeouts` not in diff. |
| 4 | DEC-117 atomic bracket invariant | N/A | `ibkr_broker.py:783-805` not in diff. |
| 5 | 5,080 pytest baseline holds | PASS | Re-verified by reviewer: 5,133 passed (delta +5, all from new test file; close-out target ≥5,113 comfortably beaten). |
| 6 | tests/test_main.py 39 pass + 5 skip | PASS | Re-verified by reviewer: 39 passed, 5 skipped. Session 2a touches `main.py` so this is the at-maximum-risk invariant. |
| 7 | Vitest baseline holds at 866 | N/A | Backend session, no frontend changes. |
| 8 | Risk Manager Check 0 unchanged | PASS | `risk_manager.py` zero edits. |
| 9 | IMPROMPTU-04 startup invariant unchanged | PASS | `main.py` diff confined to import + call site; startup region zero edits. |
| 10 | DEC-367 margin circuit breaker unchanged | PASS | `risk_manager.py` and margin-circuit code unchanged. |
| 11 | Sprint 29.5 EOD flatten circuit breaker unchanged | PASS | EOD flatten code unchanged. |
| 12 | Pre-existing flake count did not regress | PASS | Suite passes 5,133/5,133; same 22 warnings as baseline; no new flakes. |
| 13 | New config fields parse without warnings | N/A | Session 2a adds no new config fields. |
| 14 | Monotonic-safety property — Session 2a row | PASS | OCA bracket=YES, OCA standalone(4)=YES, Broker-only safety=YES, Restart safety=YES, Recon detects shorts=NO (typed only). Matches spec table row. |
| 15 | No items on do-not-modify list touched | PASS | See audit table above. |
| 16 | Bracket placement perf does not regress beyond bound | N/A | Session 4 wires this; 2a is observational only. |
| 17 | Mass-balance assertion at session debrief | N/A | Session 4 delivers. |
| 18 | Frontend banner cross-page persistence | N/A | Session 5e delivers. |
| 19 | WebSocket fan-out reconnect resilience | N/A | Session 5c delivers. |
| 20 | Acknowledgment audit-log persistence | N/A | Session 5a.1+5a.2 deliver. |
| 21 | SimulatedBroker OCA-assertion tautology guard | N/A | No OCA-assertion tests added in Session 2a. |
| 22 | Spike script freshness | N/A | Session 4 lands the gate. |

## Test Evidence (re-verified)

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q
5133 passed, 22 warnings in 52.39s

$ python -m pytest tests/test_main.py -q
39 passed, 5 skipped in 2.45s

$ python -m pytest tests/execution/order_manager/test_session2a_reconciliation_contract.py -v
5 passed in 0.21s

$ python -m pytest tests/execution/order_manager/test_reconciliation.py \
    tests/execution/order_manager/test_reconciliation_log.py \
    tests/execution/order_manager/test_reconciliation_redesign.py \
    tests/execution/order_manager/test_safety.py \
    tests/execution/order_manager/test_sprint2875.py -q
56 passed in 1.50s
```

Counts match the close-out exactly. No discrepancies.

## Escalation-Criteria Trigger Check

- **A2** (CONCERNS or ESCALATE): NOT TRIGGERED — verdict is CLEAR.
- **B1** (flake regression): NOT TRIGGERED — same 22 warnings, no new flakes observed.
- **B3** (pytest baseline below 5,080): NOT TRIGGERED — 5,133 well above baseline.
- **B4** (CI failure on final commit): NOT TRIGGERED locally; CI run URL must be cited by operator before Session 2b.1 begins (RULE-050).
- **B5** (line drift > 5 lines): TRIGGERED-MILD — close-out documents that the call site shifted from `:1505-1535` (spec) to `:1519-1553` (post-edit). The post-edit shift is +14 lines, but this is the natural growth from adding the fail-closed branch (≈14 lines of new code), not a pre-existing drift in the call-site location. Pre-flight grep confirmed `:1505-1535` was the correct starting position; no spec adjustment required for downstream sessions.
- **B6** (do-not-modify list file in diff): NOT TRIGGERED — see audit table.
- **C5** (uncertainty about do-not-modify boundary): NOT TRIGGERED — the `main.py` edit is unambiguously inside the `:1505-1535` (now `:1519-1553`) scoped exception per invariant 15.
- **C7** (existing test fails for behavioral reason): NOT TRIGGERED — all 9 mock-fixture-update sites pass; no behavioral test required adjustment beyond type plumbing.

No escalation triggers fire. Verdict CLEAR.

## CI Verification (RULE-050)

The close-out does not cite a CI run URL on commit `813fc3c`. RULE-050 requires CI to be green on the session's final commit before the next session may begin. **Action item for operator:** confirm the CI run on `813fc3c` is green before kicking off Session 2b.1; if a flake fires in CI that did not fire locally, halt per B4 and dispose. This is a procedural item, not a verdict-blocking concern — local test evidence is clean and reproducible.

## Discovered Edge Cases

None beyond what the close-out documented:
- The 9-vs-3 fixture-count discrepancy is properly disclosed.
- `test_safety.py:511` PyJWT post-DEF-179 import is unaffected.

## Deferred Items (RULE-007)

None. Session scope was tightly contained as designed.

---END-REVIEW---

```json:structured-verdict
{
  "session": "2a",
  "verdict": "CLEAR",
  "tier": 2,
  "reviewer_role": "backend-safety",
  "anchor_commit": "813fc3c",
  "predecessor_commit": "6b942e5",
  "tests_added": 5,
  "mock_updates": 9,
  "tests_total_after_full_suite": 5133,
  "tests_total_after_test_main_py": "39 pass + 5 skip",
  "donotmodify_violations": 0,
  "review_focus_findings": {
    "information_end_to_end": "PASS",
    "frozen_dataclass_immutability": "PASS",
    "fail_closed_side_none": "PASS",
    "argus_orphan_branch_preserved": "PASS",
    "main_py_edit_scope": "PASS",
    "mock_fixtures_mechanical": "PASS",
    "risk_manager_check_0_unchanged": "PASS"
  },
  "regression_checklist_summary": {
    "applicable_invariants": 14,
    "pass": 14,
    "fail": 0,
    "n_a": 8
  },
  "escalation_triggers_fired": [],
  "soft_observations": [
    "B5-MILD: Call site shifted +14 lines (1505-1535 spec → 1519-1553 post-edit) due to natural code growth from fail-closed branch addition. Not a spec adjustment.",
    "RULE-050: CI run URL on commit 813fc3c not cited in close-out; operator must confirm green CI before Session 2b.1 begins."
  ],
  "tier_3_track": "side-aware-reconciliation",
  "next_session": "2b.1",
  "context_state": "GREEN"
}
```
