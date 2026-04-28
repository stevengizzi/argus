# Sprint 31.91, Session 2a — Close-Out Report

> **Track:** Side-Aware Reconciliation Contract (Sessions 2a → 2b.1 → 2b.2 → 2c.1 → 2c.2 → 2d).
> **Position in track:** First session — typed-contract refactor only.
> **Verdict:** PROPOSED_CLEAR (pending Tier 2).
> **Date:** 2026-04-27.

## Summary

Refactored the reconciliation contract from a side-stripped
`dict[str, float]` (`{symbol: shares}`) to a typed
`dict[str, ReconciliationPosition]` (`{symbol: ReconciliationPosition(symbol, side, shares)}`).
The new dataclass is frozen with defensive `__post_init__` checks
(`shares > 0`, `side is not None`); the call site at `argus/main.py`
fails closed on `Position.side is None` rather than fabricating a
default direction.

Session 2a is the structural refactor only — orphan-loop branch
detection (broker-orphan SHORT → `phantom_short` alert) lands in
Session 2b.1; side-aware reads at the four count-filter sites land in
Session 2b.2. The existing ARGUS-orphan branch behavior is preserved
end-to-end (regression-protection Test 4 green).

## Files Modified

| File | Change | Approx. line range |
|------|--------|---------|
| `argus/execution/order_manager.py` | `+ReconciliationPosition` frozen dataclass; `reconcile_positions` signature + body type plumbing (`broker_positions[sym]` → `broker_positions[sym].shares`) | dataclass at `:171-204`; reconcile_positions at `:3343-3384` (was `:3309-3346`) |
| `argus/main.py` | Import `ReconciliationPosition`; call site rewrite to build typed dict with fail-closed `side is None` skip + CRITICAL log | import at `:95`; call site at `:1519-1553` (was `:1519-1531`) |
| `tests/execution/order_manager/test_session2a_reconciliation_contract.py` | NEW — 5 tests covering the contract refactor | `+349 LOC` |
| `tests/execution/order_manager/test_reconciliation.py` | Mock fixture updated: `dict[str, float]` → `dict[str, ReconciliationPosition]` (1 site with value, 1 empty annotation) | `:30 imports`, `:236, :302` |
| `tests/execution/order_manager/test_reconciliation_log.py` | Mock fixture updated: 2 sites with values | `:13 imports`, `:42, :64` |
| `tests/execution/order_manager/test_reconciliation_redesign.py` | Mock fixture updated: 1 site with value (`GHOST` symbol miss-counter reset) | `:30 imports`, `:319` |
| `tests/execution/order_manager/test_safety.py` | Mock fixture updated: 5 sites with values | `:30 imports`, `:417, :436, :454, :546, :1019` |
| `tests/execution/order_manager/test_sprint2875.py` | Type-annotation update on empty dict (no value to construct) | `:36 imports`, `:521` |

**Mock fixture updates:** 9 distinct call sites across 5 test files (the
pre-flight grep estimated ~3; the actual count is higher because
`test_safety.py` has 5 reconciliation tests and `test_reconciliation_log.py`
has 2). All updates are mechanical — replacing `{"SYM": 100.0}` with
`{"SYM": ReconciliationPosition(symbol="SYM", side=OrderSide.BUY, shares=100)}`,
or updating the type annotation on an empty dict.

## Tests Added

1. **`test_reconciliation_position_dataclass_frozen_round_trip`** —
   Protects: frozen-dataclass mutability AND `__post_init__` defensive
   checks. Mutation raises `FrozenInstanceError`; `shares <= 0` and
   `side is None` raise `ValueError`. Reverting `frozen=True` or
   removing `__post_init__` makes this test fail.
2. **`test_reconcile_positions_signature_typed_dict`** — Protects: the
   new signature accepts the typed dict end-to-end through the body
   AND structurally rejects the old `dict[str, float]` shape (raises
   `AttributeError` on `.shares` access). Reverting the body to
   `int(broker_positions.get(symbol, 0))` makes the negative-case
   assertion fail.
3. **`test_main_call_site_builds_typed_dict_from_broker_positions`** —
   Protects: `main.py`'s loop body produces `ReconciliationPosition`
   instances with the broker's side preserved. Drives one iteration of
   `_run_position_reconciliation` via `monkeypatch.setattr(asyncio.sleep)`
   and asserts the dict passed to `reconcile_positions` has correct
   side/shares. Reverting the call site to the old `qty = float(...)`
   shape makes this test fail because the mock receives floats not
   `ReconciliationPosition` instances.
4. **`test_argus_orphan_branch_unchanged_with_typed_contract`** —
   Regression-protection test. ARGUS has 100 AAPL; broker reports
   nothing (empty typed dict); orphan branch must fire with
   `ExitReason.RECONCILIATION` and close the position. Reverting the
   reconcile_positions body in any way that drops the orphan-detection
   branch makes this test fail.
5. **`test_reconcile_positions_with_pos_missing_side_attribute_fails_closed`** —
   Protects the call site's fail-closed `side is None` branch. A
   `Position` with `side=None` is SKIPPED at the call site (not passed
   to `reconcile_positions`); the loop logs CRITICAL and continues
   reconciling the remaining well-formed positions. Reverting to a
   "fabricate default side" pattern makes this test fail because the
   mock would receive a `ReconciliationPosition` for `BADSYM`.

## Git Diff Stat

```
 argus/execution/order_manager.py                   | 53 ++++++++++++++++++++--
 argus/main.py                                      | 39 +++++++++++++---
 tests/execution/order_manager/test_reconciliation.py |  9 ++--
 tests/execution/order_manager/test_reconciliation_log.py       | 15 ++++--
 tests/execution/order_manager/test_reconciliation_redesign.py  |  7 ++-
 tests/execution/order_manager/test_safety.py       | 23 +++++++---
 tests/execution/order_manager/test_sprint2875.py   | 10 ++--
 tests/execution/order_manager/test_session2a_reconciliation_contract.py | +349 LOC (new file)
 8 files changed, 478 insertions(+), 27 deletions(-)
```

## Test Evidence

### Baseline (pre-Session-2a, anchor commit `49beae2` — Session 1c verdict CLEAR)

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q
5128 passed, 23 warnings in 56.56s

$ python -m pytest tests/test_main.py -q
39 passed, 5 skipped in 4.38s
```

### After Session 2a

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q
5133 passed, 23 warnings in 64.72s

$ python -m pytest tests/test_main.py -q
39 passed, 5 skipped in 7.52s
```

**Delta:** `5128 → 5133` (+5), exactly the count of new tests added in
Session 2a. Zero regressions. Per RULE-019, the post-session count is
greater than or equal to the baseline; per RULE-019 + the session's
explicit ≥ 5,113 target, baseline is comfortably beaten. test_main.py
held at 39 + 5 skip — Session 2a edits `main.py`, so this invariant was
at maximum risk and is verified clean.

## Do-Not-Modify Audit

`git diff --name-only` modified files list (8 files):
- `argus/execution/order_manager.py` (in scope)
- `argus/main.py` (in scope, scoped exception per invariant 15)
- `tests/execution/order_manager/test_reconciliation.py` (mock update)
- `tests/execution/order_manager/test_reconciliation_log.py` (mock update)
- `tests/execution/order_manager/test_reconciliation_redesign.py` (mock update)
- `tests/execution/order_manager/test_safety.py` (mock update)
- `tests/execution/order_manager/test_sprint2875.py` (mock update)
- `tests/execution/order_manager/test_session2a_reconciliation_contract.py` (new file)

All do-not-modify entries verified clean (`git diff` returned empty for each):

| File | Status |
|------|--------|
| `argus/execution/order_manager.py:1670-1750` (DEF-199 A1) | UNCHANGED — diff hunks at `:171, :3343, :3352, :3379` only |
| `argus/main.py` startup invariant region (`check_startup_position_invariant`) | UNCHANGED — diff hunks at `:92` (import) and `:1516-1553` (scoped call site) only |
| `argus/models/trading.py:153-173` Position class | UNCHANGED — file not in diff list |
| `argus/execution/alpaca_broker.py` | UNCHANGED — file not in diff list |
| `argus/data/alpaca_data_service.py` | UNCHANGED — file not in diff list |
| `argus/execution/ibkr_broker.py` | UNCHANGED — file not in diff list |
| `argus/execution/broker.py` | UNCHANGED — file not in diff list |
| `argus/core/risk_manager.py` (Session 2b.2 modifies; not 2a) | UNCHANGED — file not in diff list |
| `argus/core/health.py` | UNCHANGED — file not in diff list |
| `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` | UNCHANGED — file not in diff list |
| `workflow/` submodule | UNCHANGED — file not in diff list |

`git diff argus/execution/order_manager.py` hunk headers verified:
```
@@ -168,6 +168,40 @@ class ReconciliationResult:
@@ -3309,7 +3343,7 @@ class OrderManager:
@@ -3318,8 +3352,17 @@ class OrderManager:
@@ -3336,14 +3379,16 @@ class OrderManager:
```
Lines `1670-1750` (DEF-199 A1 fix region) are NOT in any hunk.

`git diff argus/main.py` hunk headers verified:
```
@@ -92,7 +92,7 @@ from argus.db.manager import DatabaseManager
@@ -1516,14 +1516,41 @@ class ArgusSystem:
```
The startup invariant region (`check_startup_position_invariant()`,
IMPROMPTU-04 fix) is NOT in any hunk.

## Discovered Edge Cases

- `test_safety.py` and `test_reconciliation_log.py` both have multiple
  reconciliation tests; the pre-flight grep "expect ~3 mock updates"
  underestimated. Actual: 9 distinct call sites across 5 files. All
  are mechanical updates with no behavioral change (per RULE-038
  spirit: surface the kickoff-vs-actual discrepancy in the close-out
  rather than silently conform).
- `test_safety.py:511` already imports `jwt` (PyJWT post-DEF-179) — no
  change needed for that test infrastructure.

## Deferred Items (RULE-007)

None. The session scope was tightly contained (typed-contract refactor
only). Side-aware orphan-detection branches and side-aware count-filter
reads are explicit follow-ons in Sessions 2b.1 and 2b.2 respectively
and were not in Session 2a's scope.

## Sprint-Level Regression Checklist

- **Invariant 5 (5,080+ pytest baseline holds):** PASS — 5,133 ≥ 5,113 target.
- **Invariant 6 (`tests/test_main.py` 39+5):** PASS — verified 39 passed, 5 skipped after the `main.py` edit.
- **Invariant 8 (Risk Manager Check 0 unchanged):** PASS — `argus/core/risk_manager.py` not in diff list (zero edits).
- **Invariant 9 (IMPROMPTU-04 startup invariant unchanged):** PASS — `main.py` diff hunks confined to `:92` (import) and `:1516-1553` (scoped call site); `check_startup_position_invariant()` region untouched.
- **Invariant 14 (Monotonic-safety property — Session 2a row):** OCA bracket = YES; OCA standalone (4) = YES; Broker-only safety = YES; Restart safety = YES; Recon detects shorts = NO (typed only — typed contract enables 2b.1's branch, 2a alone does not detect).
- **Invariant 15 (do-not-modify list untouched):** PASS — see audit table above.

## Verdict

```json
{
  "session": "2a",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 5,
  "mock_updates": 9,
  "tests_total_after": 5133,
  "test_main_py_count": "39 pass + 5 skip",
  "files_modified": [
    "argus/execution/order_manager.py",
    "argus/main.py",
    "tests/execution/order_manager/test_reconciliation.py",
    "tests/execution/order_manager/test_reconciliation_log.py",
    "tests/execution/order_manager/test_reconciliation_redesign.py",
    "tests/execution/order_manager/test_safety.py",
    "tests/execution/order_manager/test_sprint2875.py",
    "tests/execution/order_manager/test_session2a_reconciliation_contract.py"
  ],
  "donotmodify_violations": 0,
  "tier_3_track": "side-aware-reconciliation"
}
```

## Context State

GREEN — single-session work, well within context limits, no
compaction. Pre-flight, baseline, edits, and post-flight all completed
without intermediate context pressure.
