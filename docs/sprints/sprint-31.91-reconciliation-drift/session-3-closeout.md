# Sprint 31.91 Session 3 — Close-Out Report

> **Track:** D6 single-session track (DEF-158 retry side-check + severity fix). Independent of the side-aware reconciliation contract track but consumes its `phantom_short` alert taxonomy via a sibling `phantom_short_retry_blocked` alert_type.
> **Self-assessment:** **CLEAN** (PROPOSED_CLEAR pending Tier 2 verdict).
> **Context State:** GREEN.

---

## Verdict JSON

```json
{
  "session": "3",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 5,
  "improptu_04_pattern_mirrored": true,
  "all_branches_clear_flatten_pending": true,
  "def158_anti_regression_pass": true,
  "files_modified": [
    "argus/execution/order_manager.py",
    "tests/execution/order_manager/test_def158.py",
    "tests/execution/order_manager/test_sprint295.py"
  ],
  "files_added": [
    "tests/execution/order_manager/test_def204_session3_retry_side_check.py"
  ],
  "donotmodify_violations": 0
}
```

---

## Change Manifest

### `argus/execution/order_manager.py`

The DEF-158 retry path inside `_check_flatten_pending_timeouts` (line 3171) is the last side-blind retry shape in the OrderManager. Session 3 closes it.

- **Inside the broker-position query loop** (line 3258-3267): captured `broker_side: Any = getattr(bp, "side", None)` alongside the existing `broker_qty = abs(int(getattr(bp, "shares", 0)))`. The capture follows IMPROMPTU-04 EOD A1's idiom at `:1864-1874`.
- **After the existing `broker_qty == 0` early-return** (line 3275): added the 3-branch side-aware gate (line 3276-3341). Branch ordering preserves the architectural property that SELL-of-short is structurally prevented before the qty-mismatch logic runs:
  - **Branch 1** — `broker_side == OrderSide.BUY` falls through to the existing qty-mismatch update + flatten resubmit (no behaviour change to the DEF-158 happy path).
  - **Branch 2** — `broker_side == OrderSide.SELL` triggers `logger.critical(...)` + emits a `SystemAlertEvent(alert_type="phantom_short_retry_blocked", severity="critical", ...)` with structured metadata (symbol / broker_shares / broker_side / expected_side / detection_source) + clears `_flatten_pending` to prevent infinite re-emission + `continue`s the outer loop. Place_order is NEVER called.
  - **Branch 3** — any other `broker_side` (None / unrecognized) triggers `logger.error(...)` + clears `_flatten_pending` + `continue`s. No alert emitted (defensive code path; alert flooding on a structural broker-adapter defect would not be useful).
- **Exception path preserved verbatim**: the legacy `except Exception:` fallthrough still uses ARGUS-tracked `position.shares_remaining` if the broker query itself raises. The 3-branch gate sits inside the `try` block, so failure-to-query continues to use the legacy fallback (avoids over-tightening tests that exercise the Exception path with un-configured AsyncMocks).
- **OCA-EXEMPT comment refreshed** (line 3367-3374): the pre-Session-3 comment said "Session 3 will branch this on side"; updated to record that Session 3 has now landed the upstream side gate and the retry SELL remains structurally OCA-exempt because the original flatten's OCA siblings were already drained at first dispatch by `_flatten_position`. The `# OCA-EXEMPT:` marker remains so the `tests/_regression_guards/test_oca_threading_completeness.py` guard continues to pass.

Pre-existing branches NOT touched (per spec D6 "preserved verbatim"):
- `broker_qty == 0` early-return.
- The qty-mismatch path that updates `sell_qty = broker_qty` when ARGUS-tracked != broker count.
- The retry-cap / cycle-count / abandonment logic above the broker query block.
- The fresh-market-sell submission block below the gate (now reached only when broker_side is BUY).

### `tests/execution/order_manager/test_def204_session3_retry_side_check.py` *(new)*

5 new pytest cases:

1. `test_def158_retry_long_position_flattens_normally` — Branch 1 happy path. Broker reports `MagicMock(symbol="AAPL", shares=100, side=OrderSide.BUY)`; assert `place_order` called once with `side=OrderSide.SELL, quantity=100`; assert `_flatten_pending["AAPL"][0] == "resubmit-1"`.
2. `test_def158_retry_short_position_blocks_and_alerts_critical` — Branch 2. Broker reports `side=OrderSide.SELL`; assert `place_order.assert_not_called()`; assert exactly one `SystemAlertEvent(alert_type="phantom_short_retry_blocked", severity="critical")` captured after `await event_bus.drain()`; assert `_flatten_pending` cleared; assert CRITICAL log line present in `caplog`.
3. `test_def158_retry_unknown_side_blocks_and_logs_error` — Branch 3. Broker reports `side=None`; assert `place_order.assert_not_called()`; assert NO `SystemAlertEvent` emitted (defensive log-only branch); assert ERROR log line present; assert `_flatten_pending` cleared.
4. `test_def158_retry_qty_mismatch_long_uses_broker_qty` — DEF-158 anti-regression. Broker reports `shares=80, side=OrderSide.BUY` while ARGUS thinks 100; assert SELL placed with `quantity=80` (not 100). The qty-mismatch path is preserved; only the side-blindness was changed.
5. `test_phantom_short_retry_blocked_alert_severity_is_critical` — Focused payload verification. Asserts `alert.alert_type == "phantom_short_retry_blocked"`, `alert.severity == "critical"`, `alert.source == "order_manager._check_flatten_pending_timeouts"`, and the full structured metadata dict (symbol / broker_shares / broker_side="SELL" / expected_side="BUY" / detection_source="def158_retry").

The new file uses the same fixture style as `test_session2b2_pattern_a_b.py` (the canonical Session 2b.2 pattern): MagicMock broker with AsyncMock methods, `_capture_alerts(event_bus)` helper, `await event_bus.drain()` after triggering to flush handler tasks before assertions.

### `tests/execution/order_manager/test_def158.py` *(mock fixture update)*

`test_flatten_timeout_does_resubmit_when_broker_position_exists` (line 217) — the pre-existing test injects `MagicMock(symbol="ARX", shares=103)` as the broker position. Without an explicit `side` attribute, `getattr(bp, "side", None)` returns a MagicMock (auto-attribute) instead of `None`, which would route the test through the new Branch 3 (unknown side, refuse retry). Updated to `MagicMock(symbol="ARX", shares=103, side=OrderSide.BUY)` with an inline comment explaining the post-Session-3 contract. Also added `OrderSide` to the import block.

### `tests/execution/order_manager/test_sprint295.py` *(mock fixture update)*

`test_flatten_error_404_requery_qty` (line 194-201) — the pre-existing test stages a `MagicMock` broker position without `side`. Same root cause as the test_def158.py fixture. Set `broker_pos.side = OrderSide.BUY` with an inline comment. `OrderSide` was already imported.

---

## Pattern Symmetry Note

Session 3's branch-2 and branch-3 code at `argus/execution/order_manager.py:3276-3341` mirrors IMPROMPTU-04 EOD A1 fix at `:1875-1904` line-for-line in shape:

| Concern | IMPROMPTU-04 (`:1875-1904`) | Session 3 (`:3276-3341`) |
|---|---|---|
| Branch ordering | BUY → flatten / SELL → log+halt / unknown → log+halt | identical |
| Long-position log level | `logger.warning("EOD flatten: retrying long ...")` | (Branch 1 falls through to existing `logger.warning("Flatten qty mismatch ...")` for the qty-mismatch case) |
| Short-position log level | `logger.error("EOD flatten (Pass 1 retry): DETECTED UNEXPECTED SHORT POSITION ...")` | `logger.critical("Flatten retry refused for %s: broker reports SHORT ...")` (upgraded to CRITICAL per spec D6 — this site escalates to operator-page severity, while the EOD Pass 1 retry only logs ERROR because EOD Pass 2 then re-detects the same short and emits the `phantom_short` alert) |
| Unknown-side log level | `logger.error("EOD flatten (Pass 1 retry): position %s has unknown side ...")` | `logger.error("Flatten retry refused for %s: broker side is %r ...")` |
| Investigate-via-script callout | "Investigate and cover manually via scripts/ibkr_close_all_positions.py." | "Investigate via scripts/ibkr_close_all_positions.py." (Branch 2) |
| `place_order` skip on SHORT | implicit via the `elif retry_side == OrderSide.SELL: logger.error(...)` block returning without further action | explicit `continue` after alert+pop |
| `place_order` skip on unknown | implicit via the `else: logger.error(...)` block | explicit `continue` after pop |

**Key intentional deviations from IMPROMPTU-04:**

1. **CRITICAL vs ERROR on the SHORT branch.** IMPROMPTU-04 EOD Pass 1 retry uses `logger.error`. Session 3 uses `logger.critical` because:
   - Spec D6 explicitly requires `severity="critical"` on the `phantom_short_retry_blocked` alert.
   - The DEF-158 retry path is operator-page surface — the next reconciliation cycle will re-trigger the same path, and ARGUS has no other detection mechanism between cycles. Compare to EOD Pass 1 retry, which is followed by EOD Pass 2's own SHORT detection that emits the canonical `phantom_short` alert (Session 2b.2 Pattern B); Pass 1 retry is the first observation but not the operator-page emission.
2. **Explicit `_flatten_pending.pop` + `continue`** in branches 2 and 3. IMPROMPTU-04's EOD Pass 1 retry path naturally terminates after the per-symbol log; Session 3 must explicitly clear `_flatten_pending` because the retry function is itself called every poll cycle — without the pop, branches 2 and 3 would re-emit the alert/log every poll forever.
3. **Alert in branch 2 only.** IMPROMPTU-04's EOD Pass 1 retry emits no alert (the alert lives in EOD Pass 2). Session 3's branch 2 emits a `phantom_short_retry_blocked` alert because this site is the first AND only observer of the phantom condition during normal-session retry — there is no downstream "Pass 2" to defer the alert to.

The metadata shape is taxonomically aligned with the existing `phantom_short` alerts (Session 2b.1 reconciliation, Session 2b.2 EOD Pass 2, Session 2b.2 Health integrity check) so Session 5a.2's auto-resolution policy table can route by `alert_type` while sharing severity routing logic. The new `phantom_short_retry_blocked` alert_type is intentionally distinct from `phantom_short` so the policy table can differentiate "retry-side detection (refused SELL)" from "reconciliation-side detection (gate engagement)" if Session 5a.2 wants different resolution paths.

---

## Scope Verification

**In scope (delivered):**
- ✅ 3-branch side-aware gate at `_check_flatten_pending_timeouts:~3276`.
- ✅ `phantom_short_retry_blocked` alert with `severity="critical"` + structured metadata.
- ✅ All 3 branches clear `_flatten_pending` (no infinite retry).
- ✅ DEF-158 qty-mismatch normal case anti-regression (test 4).
- ✅ Mock fixture updates on 2 pre-existing test files (RULE-019 — additive `side=OrderSide.BUY` defaults, no test deletions).
- ✅ OCA-EXEMPT comment refreshed for post-Session-3 state.

**Out of scope (preserved verbatim per spec):**
- IMPROMPTU-04 EOD A1 fix at `:1670-1750` — zero edits (Tier 2 may verify via `git diff`).
- `argus/main.py` — zero edits.
- `argus/models/trading.py` — zero edits.
- Alpaca files — zero edits.
- `IMPROMPTU-04-closeout.md` — zero edits.
- `workflow/` — zero edits.

**Out of scope (intentionally NOT done):**
- OCA group threading on the retry SELL — not in spec D6. The retry is a fresh standalone SELL with no live OCA peers (the original flatten's siblings were drained at first dispatch); the OCA-EXEMPT marker stays in place.
- Behavioural change to the broker-query Exception path — preserved as legacy fallback to ARGUS qty so existing tests (test_sprint2875.py `test_flatten_pending_timeout_resubmits` and siblings) continue passing without further fixture updates.

---

## Regression Checks

- **Sprint-31.91 Invariant 1 (DEF-199 A1 fix):** PASS — `:1670-1750` zero edits (verified via `git diff HEAD~1 argus/execution/order_manager.py`).
- **Sprint-31.91 Invariant 3 (DEF-158 dup-SELL prevention for ARGUS=N, IBKR=N):** PASS — qty-mismatch path preserved; new test 4 (`test_def158_retry_qty_mismatch_long_uses_broker_qty`) asserts SELL qty comes from broker (80) not ARGUS (100).
- **Sprint-31.91 Invariant 5 (test count delta):** PASS — pre-Session-3 baseline +5; full-suite `5,174 passed` (zero failures, zero new skips).
- **Sprint-31.91 Invariant 14 (Monotonic-safety, "After Session 3" row):** PASS — DEF-158 retry side-aware = YES.
- **Sprint-31.91 Invariant 15:** PASS — no test deletions or skip additions.
- **OCA threading regression guard** (`tests/_regression_guards/test_oca_threading_completeness.py`): PASS — the refreshed OCA-EXEMPT comment retains the `# OCA-EXEMPT:` marker the guard scans for.

---

## Test Results

```
tests/execution/order_manager/test_def204_session3_retry_side_check.py
  test_def158_retry_long_position_flattens_normally               PASSED
  test_def158_retry_short_position_blocks_and_alerts_critical     PASSED
  test_def158_retry_unknown_side_blocks_and_logs_error            PASSED
  test_def158_retry_qty_mismatch_long_uses_broker_qty             PASSED
  test_phantom_short_retry_blocked_alert_severity_is_critical     PASSED

Pre-existing tests on _check_flatten_pending_timeouts (mock-updated):
  tests/execution/order_manager/test_def158.py    PASSED (4/4)
  tests/execution/order_manager/test_sprint295.py PASSED (8/8)
  tests/execution/order_manager/test_sprint2875.py PASSED (no fixture updates needed; Exception fallthrough preserved)

Scoped scope (tests/execution/ + tests/_regression_guards/):
  493 passed (baseline 488 + 5)

Full suite (--ignore=tests/test_main.py -n auto):
  5174 passed in 55.66s
  0 failures
```

---

## CI Status

CI verification pending push (Universal RULE-050 — Tier 2 must verify CI green on the session's final commit).

---

## Self-Assessment

**CLEAN.** No deviations from spec D6. The 3-branch gate mirrors IMPROMPTU-04 idiom precisely (with documented intentional log-level escalation on the SHORT branch and explicit pop/continue plumbing required by the per-poll-cycle nature of `_check_flatten_pending_timeouts`). All 5 requirements satisfied; all do-not-modify regions zero-edited; DEF-158 anti-regression test passes. Test delta exactly matches the spec's `~5 new` budget.

---

## Tier 2 Review Invocation

- Reviewer template: `templates/review-prompt.md` (backend safety reviewer).
- Reviewer output path: `docs/sprints/sprint-31.91-reconciliation-drift/session-3-review.md`.
- Provide: this close-out, `review-context.md`, `git diff HEAD~1`, scoped command `python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q`, and the do-not-modify list from the impl prompt.

### Session-Specific Review Focus

1. **IMPROMPTU-04 mirror verification.** Compare `:3276-3341` (Session 3) to `:1875-1904` (IMPROMPTU-04). Use the Pattern Symmetry Note above as the side-by-side reference. Verify branch ordering, log-level rationale (CRITICAL vs ERROR documented), alert metadata shape parity, and the explicit pop/continue plumbing.
2. **All 3 branches clear flatten-pending.** Trace each exit path:
   - Branch 1 (BUY): falls through to the existing flatten resubmit, which on success rebinds `_flatten_pending[symbol]` to the new order id (line 3411). Failure on `place_order` is logged (`logger.exception("CRITICAL: Flatten resubmit failed ...")`) and `_flatten_pending` is NOT cleared on the failure path — this is preserved pre-Session-3 behaviour and is correct (the next poll cycle will retry until `max_flatten_retries`).
   - Branch 2 (SELL): explicit `self._flatten_pending.pop(symbol, None)` at line 3323 before `continue`.
   - Branch 3 (unknown): explicit `self._flatten_pending.pop(symbol, None)` at line 3340 before `continue`.
3. **Alert severity is `critical`, not `warning`.** Verified via test 5 (`test_phantom_short_retry_blocked_alert_severity_is_critical`).
4. **`broker_side == OrderSide.SELL` comparison shape.** `Position.side` is `OrderSide` (StrEnum, str subclass) — the comparison `broker_side == OrderSide.SELL` is correct for both enum-instance and string-literal forms (StrEnum provides `__eq__` against strings via its str inheritance). The `getattr(bp, "side", None)` defaults to `None` if the broker adapter omits the field, and Branch 3 catches that. IMPROMPTU-04 uses the identical `retry_side == OrderSide.BUY/SELL` idiom at `:1878/1888`.
5. **No edits to `:1670-1750`.** `git diff HEAD~1 -- argus/execution/order_manager.py` should show all hunks at lines ≥3258. (Verified locally: yes.)
6. **DEF-158 normal case unchanged.** Test 4 (`test_def158_retry_qty_mismatch_long_uses_broker_qty`) is the explicit anti-regression. Pre-existing tests `test_flatten_timeout_does_resubmit_when_broker_position_exists` (test_def158.py) and `test_flatten_error_404_requery_qty` (test_sprint295.py) still PASS after the additive `side=OrderSide.BUY` mock-fixture updates.
7. **Mock fixture updates are scoped.** Two test files updated; both updates are additive (`side=OrderSide.BUY` on the existing MagicMock construction) with inline comments explaining the post-Session-3 contract. No tests deleted or skipped (RULE-019 satisfied).
8. **`phantom_short_retry_blocked` is a NEW alert_type.** Session 2b.1/2b.2 use `phantom_short`; Session 3 uses `phantom_short_retry_blocked`. Same severity (critical), distinct alert_type so Session 5a.2's policy table can route them separately. Verified via grep: the new alert_type appears only in Session 3's emission site + the new test file.

---

*End Sprint 31.91 Session 3 close-out.*
