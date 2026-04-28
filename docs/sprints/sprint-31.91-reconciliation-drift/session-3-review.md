# Sprint 31.91 Session 3 — Tier 2 Code Review

> **Reviewer:** @reviewer subagent (read-only mode per RULE-013)
> **Session under review:** 3 — DEF-158 Retry Side-Check + Severity Fix (D6)
> **Commit reviewed:** `a11c001` (parent `fda4a12`)
> **Branch:** `main`
> **Verdict:** **CLEAR**

---

---BEGIN-REVIEW---

## Summary

Session 3 closes the last side-blind retry path in `OrderManager` by inserting a 3-branch side-aware gate inside `_check_flatten_pending_timeouts` (now at `argus/execution/order_manager.py:3258-3341`), mirroring IMPROMPTU-04's EOD A1 fix idiom (`:1860-1904`). The implementation precisely matches spec D6:

- **Branch 1** (`broker_side == OrderSide.BUY`) falls through to the existing flatten-resubmit code with no behaviour change to the DEF-158 happy path.
- **Branch 2** (`broker_side == OrderSide.SELL`) emits a `phantom_short_retry_blocked` `SystemAlertEvent` with `severity="critical"`, logs CRITICAL, clears `_flatten_pending`, and `continue`s.
- **Branch 3** (`broker_side` is None / unrecognized) logs ERROR, clears `_flatten_pending`, and `continue`s without emitting an alert (defensive log-only branch).

5 new tests added (the spec's exact budget); 2 pre-existing test mock fixtures additively updated (`side=OrderSide.BUY` defaults); zero test deletions or new skips. Scoped suite: 488 → 493 passing (+5). Full suite per closeout: 5,174 passed in 55.66s. Do-not-modify regions all show zero edits.

CI green on commit `a11c001` (run 25035589472, both backend pytest and frontend vitest jobs success).

## Findings

### F1 — IMPROMPTU-04 mirror is faithful and the symmetry note is accurate (PASS)

The Pattern Symmetry Note in the close-out (lines 75-97) accurately reflects the diff. Verified by reading IMPROMPTU-04 EOD A1 at `argus/execution/order_manager.py:1860-1904` side-by-side with Session 3 at `:3258-3341`:

| Concern | IMPROMPTU-04 (verified) | Session 3 (verified) |
|---|---|---|
| Branch ordering | BUY=flatten / SELL=log+halt / unknown=log+halt | identical |
| `broker_side` capture | `getattr(p, "side", None)` at `:1869` | `getattr(bp, "side", None)` at `:3266` |
| SHORT branch log | `logger.error` at `:1889` | `logger.critical` at `:3284` (intentional escalation, see F2) |
| Unknown branch log | `logger.error` at `:1899` | `logger.error` at `:3326` |
| "Investigate-via-script" callout | `:1893-1894` ("scripts/ibkr_close_all_positions.py") | `:3287-3288` (same script) |
| Comparison shape | `retry_side == OrderSide.SELL` (StrEnum) | `broker_side == OrderSide.SELL` (StrEnum) |

Both intentional deviations the implementor flagged are well-justified:

1. **CRITICAL vs ERROR on the SHORT branch** — Spec D6 explicitly requires `severity="critical"` on `phantom_short_retry_blocked`. IMPROMPTU-04's Pass 1 retry uses `logger.error` because EOD Pass 2 then re-detects and emits the canonical `phantom_short` alert; the DEF-158 retry path has no downstream Pass 2 to defer to, so this site is the first AND only operator-page surface during normal-session retry.
2. **Explicit `_flatten_pending.pop(symbol, None) + continue`** — IMPROMPTU-04's EOD path naturally terminates after the per-symbol log within an outer `for sym in timed_out:` loop. Session 3's `_check_flatten_pending_timeouts` is called every poll cycle, so the explicit pop is required to prevent infinite re-emission. Without it, branches 2 and 3 would emit alerts/errors forever.

### F2 — All 3 branches clear flatten-pending (PASS)

Traced each exit path against the actual diff:

- **Branch 1 (BUY)** — falls through past line 3341 to the existing `if broker_qty != position.shares_remaining:` mismatch path (`:3342`), then to the resubmit at `:3358-3402`. On successful `place_order`, `_flatten_pending[symbol]` is rebound at `:3384-3386` to the new resubmit order id. On failure, `logger.exception` fires at `:3397-3401` and `_flatten_pending` retains the old entry — preserving pre-Session-3 retry-cap behavior (next poll cycle will retry until `max_flatten_retries`). Verified by `test_def158_retry_long_position_flattens_normally` asserting `om._flatten_pending["AAPL"][0] == "resubmit-1"`.
- **Branch 2 (SELL)** — explicit `self._flatten_pending.pop(symbol, None)` at `:3323` before `continue`. Verified by `test_def158_retry_short_position_blocks_and_alerts_critical` asserting `"AAPL" not in om._flatten_pending`.
- **Branch 3 (unknown)** — explicit `self._flatten_pending.pop(symbol, None)` at `:3340` before `continue`. Verified by `test_def158_retry_unknown_side_blocks_and_logs_error` asserting `"AAPL" not in om._flatten_pending`.

### F3 — Alert severity is critical with full structured metadata (PASS)

The new emission at `argus/execution/order_manager.py:3293-3314`:

- `severity="critical"` ✓ (spec D6 acceptance)
- `alert_type="phantom_short_retry_blocked"` ✓ (taxonomically distinct from 2b.1/2b.2's `phantom_short`)
- `source="order_manager._check_flatten_pending_timeouts"` ✓
- `metadata` populated structurally per DEF-213's typed-consumer-access contract: `{"symbol": ..., "broker_shares": ..., "broker_side": "SELL", "expected_side": "BUY", "detection_source": "def158_retry"}` ✓

`test_phantom_short_retry_blocked_alert_severity_is_critical` asserts the exact payload shape including all 5 metadata keys — the test will fail loudly if Session 5a.2's auto-resolution policy table needs to depend on a different field name.

### F4 — `phantom_short_retry_blocked` is a NEW distinct alert_type (PASS)

Verified via grep:

```
$ grep -rn "phantom_short_retry_blocked" argus/ tests/
argus/execution/order_manager.py:3296    (emission site, Session 3)
argus/execution/order_manager.py:3317    (defensive logger.exception message)
tests/execution/order_manager/test_def204_session3_retry_side_check.py:* (test references)
```

Pre-existing `phantom_short` (no suffix) emissions at `argus/main.py:1130`, `argus/core/health.py:548`, `argus/execution/order_manager.py:1958`, `argus/execution/order_manager.py:2381` (Sessions 2b.1/2b.2 entry points) are untouched. Same severity (`critical`); distinct alert_type so Session 5a.2's policy table can route them separately.

### F5 — `broker_side == OrderSide.SELL` comparison shape is correct (PASS)

`Position.side: OrderSide` at `argus/models/trading.py:177`; `OrderSide` is declared `StrEnum` at `argus/models/trading.py:31`. The comparison `broker_side == OrderSide.SELL` works for both enum-instance form (canonical Position emission) and string-literal form (defensive against broker adapter drift), because `StrEnum` inherits `str.__eq__`. The `getattr(bp, "side", None)` defaults to `None` if the broker adapter omits the field, and Branch 3 catches that. IMPROMPTU-04 uses the identical idiom at `:1878/1888`.

### F6 — Zero edits to `:1670-1750` and all other do-not-modify regions (PASS)

`git diff HEAD~1 -- argus/execution/order_manager.py` hunks: `@@ -3255,9 +3255,15 @@`, `@@ -3267,6 +3273,72 @@`, `@@ -3292,12 +3364,14 @@`. All three at line ≥3255, well outside the protected `:1670-1750` range.

`git diff HEAD~1 -- argus/main.py argus/models/trading.py 'argus/data/alpaca_*.py' argus/execution/alpaca_broker.py docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md workflow/` returns empty output — zero edits. Note the documented `:1670-1750` range is now occupied by margin-circuit and time-stop code (line numbers drifted across Sessions 0-2d); the actual IMPROMPTU-04 A1 fix has migrated to `:1860-2000+`. Session 3's hunks remain well clear of both ranges.

### F7 — DEF-158 normal case unchanged (PASS)

`test_def158_retry_qty_mismatch_long_uses_broker_qty` (test 4) asserts:
- Broker reports `shares=80, side=OrderSide.BUY`; ARGUS-tracked `shares_remaining=100`.
- After `_check_flatten_pending_timeouts()`, `place_order` is called once with `quantity=80` — the broker-authoritative count.

The qty-mismatch logic at `argus/execution/order_manager.py:3342-3350` is preserved verbatim (only the upstream side gate is new). `tests/execution/order_manager/test_def158.py::test_flatten_timeout_does_resubmit_when_broker_position_exists` and `tests/execution/order_manager/test_sprint295.py::TestFlattenError404::test_flatten_error_404_requery_qty` both pass after the additive `side=OrderSide.BUY` fixture update.

### F8 — Mock fixture updates are scoped and additive (PASS)

Two test-file diffs:
- `tests/execution/order_manager/test_def158.py:217` — `MagicMock(symbol="ARX", shares=103)` → `MagicMock(symbol="ARX", shares=103, side=OrderSide.BUY)`. Inline comment explains the post-Session-3 contract. `OrderSide` added to import block.
- `tests/execution/order_manager/test_sprint295.py:194-201` — explicit `broker_pos.side = OrderSide.BUY` line added with inline comment. `OrderSide` already imported.

Zero test deletions, zero new `@pytest.mark.skip` markers (`git diff HEAD~1 -- tests/ | grep -E "^-.*def test_|^-.*@pytest.mark.skip"` returns empty). RULE-019 satisfied.

`tests/execution/order_manager/test_sprint2875.py` requires no fixture update because its `mock_broker` fixture doesn't configure `get_positions` as `AsyncMock` — `await self._broker.get_positions()` raises, the existing `except Exception:` fallthrough at `:3351-3356` catches it and falls back to ARGUS-tracked qty. The closeout's claim about preserved Exception-path behavior is verified.

### F9 — OCA-EXEMPT comment refresh preserves the regression-guard marker (PASS)

The pre-Session-3 comment at the resubmit SELL site (line 3367-3374) is updated from "Session 3 will branch this on side" to "Sprint 31.91 Session 3 added the upstream 3-branch side gate ... so SELL-of-short is structurally prevented before this placement." The `# OCA-EXEMPT:` marker is preserved.

`tests/_regression_guards/test_oca_threading_completeness.py` runs all 4 tests green:
- `test_no_sell_without_oca_when_managed_position_has_oca` PASSED
- `test_oca_exempt_marker_recognized` PASSED
- `test_oca_threading_marker_recognized` PASSED
- `test_oca_exempt_comment_recognized` PASSED

### F10 — Test counts confirmed (PASS)

Scoped suite (per spec command): `python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q`:
- **493 passed in 16.88s** (baseline 488 + 5 new = exactly the spec's expected delta).

Full suite per close-out: 5,174 passed in 55.66s, zero failures. (Independent re-run not performed; baseline of 5,080 from review-context Invariant 5 is held.)

## Regression Checklist Results

| # | Invariant | Result |
|---|---|---|
| 1 | DEF-199 A1 fix at `:1670-1750` zero edits | PASS — diff shows hunks at `:3255+` only |
| 2 | DEF-199 A1 EOD Pass 1 retry side check still respects | PASS — inferred from F6 (region untouched) |
| 3 | DEF-158 dup-SELL prevention (ARGUS=N, IBKR=N) | PASS — test 4 explicit anti-regression |
| 4 | DEC-117 atomic bracket invariant | N/A — Session 3 doesn't touch bracket placement |
| 5 | Pre-existing 5,080 pytest baseline holds | PASS — closeout reports 5,174 in full suite (additive +5 from S3 + accumulation from S0-2d) |
| 6 | `tests/test_main.py` baseline (39 pass + 5 skip) | N/A — Session 3 doesn't touch `main.py` (closeout scope verification confirms) |
| 7 | Vitest baseline at 866 | N/A — Session 3 is backend only |
| 8 | Risk Manager check 0 unchanged | PASS — `git diff` shows zero edits to `argus/core/risk_manager.py` |
| 9 | IMPROMPTU-04 startup invariant unchanged | PASS — `git diff` shows zero edits to `argus/main.py` |
| 10 | DEC-367 margin circuit breaker unchanged | PASS — Session 3 doesn't modify margin-circuit code |
| 11 | Sprint 29.5 EOD flatten circuit breaker unchanged | PASS — Session 3 doesn't modify EOD-flatten-circuit code |
| 12 | Pre-existing flakes did not regress | PASS — observed aiosqlite warnings during scoped run match DEF-201/DEF-192 (pre-existing); no new flakes |
| 13 | New config fields parse without warnings | N/A — Session 3 introduces no new config fields |
| 14 | Monotonic-safety property at "After Session 3" row | PASS — DEF-158 retry side-aware = YES |
| 15 | No do-not-modify list items touched | PASS — verified F6 |
| 16 | Bracket placement performance | N/A — Session 3 is the retry path, not bracket placement |
| 17 | Mass-balance assertion at session debrief | N/A — delivered in Session 4 |
| 18 | Frontend banner cross-page persistence | N/A — Session 5e |
| 19 | WebSocket fan-out reconnect resilience | N/A — Session 5a.2 / 5c |
| 20 | Acknowledgment audit-log persistence | N/A — Session 5a.1 / 5a.2 |
| 21 | SimulatedBroker OCA-assertion tautology guard | PASS — Session 3 does not introduce SimulatedBroker+OCA assertions |
| 22 | Spike script freshness | N/A — Session 4 |

## Escalation Criteria Evaluation

| Criterion | Triggered? | Reasoning |
|---|---|---|
| A1 (Tier 3 review #1 mandatory after Session 1c) | N/A | Already completed 2026-04-27 |
| A2 (Tier 2 verdict CONCERNS or ESCALATE) | NO | Verdict is CLEAR |
| A3 (paper-session phantom-short accumulation) | NO | Post-merge debrief out of session scope |
| A4 (lifecycle interaction not modeled) | NO | None discovered |
| A5 (DEC-117 behavior changed) | NO | Session 3 doesn't touch bracket placement |
| A6 (regression test 4 fails) | NO | `test_def158_retry_qty_mismatch_long_uses_broker_qty` PASSED |
| B1 (flake count regressed or new undocumented flake) | NO | Observed warnings match documented DEF-201/DEF-192 |
| B2 (test count went down) | NO | +5 net |
| B3 (pytest baseline below 5,080) | NO | 5,174 |
| B4 (CI red on session's final commit, not a known flake) | NO | CI green on `a11c001` (run 25035589472) |
| B5 (line-number drift >5 lines from spec) | YES (informational) | Spec D6 named `:2384` but the function is now at `:3171+` due to Session 0-2d accumulation; the drift is acknowledged in the closeout's change manifest and adapted-against-actual-line-numbers, per RULE-038. Not an escalation. |
| B6 (do-not-modify file in diff) | NO | Verified F6 |
| B7 (test runtime degraded >2× or single test >60s) | NO | Scoped suite ran in 16.88s (within historical baseline) |
| C1-C7 | N/A | None applicable |

## Notable Items (Not Blockers)

- **Line-number drift acknowledged.** The spec D6 anchored the insertion point at `:2384`, but the function had drifted to `:3171+` by the time Session 3 began (Sessions 0-2d added significant code above this site). The implementor adapted to actual line numbers per RULE-038 and documented the drift in the change manifest. This is C6 (acknowledged drift) rather than B5 (>5 line drift requiring halt) — the function's identity (`_check_flatten_pending_timeouts`) remained stable; only its absolute file offset changed.

- **Defensive `try/except` around `event_bus.publish`** at `:3315-3320` (Branch 2) is marked `# pragma: no cover - defensive`. This protects against an event-bus subscriber misbehavior preventing the `_flatten_pending.pop` from running, which would otherwise create an infinite alert-emission loop. Idiomatic and safe.

- **Test 3 (Branch 3) tightens assertion to "no SystemAlertEvent at all"** rather than just "no `phantom_short_retry_blocked`". This guards against a future regression where someone adds an alert to Branch 3; the assertion will require a deliberate test update at that time. Slightly stronger than the spec required but defensive in the same direction as the implementation. Aligned with the spec's "alert flooding on a structural defect would not be useful" rationale.

## Verdict

**CLEAR.** All 7 spec D6 acceptance items satisfied, all 8 Definition-of-Done items checked, all sprint-level invariants applicable to Session 3 hold, CI green on the final commit per RULE-050, the IMPROMPTU-04 mirror is faithful with two well-justified intentional deviations, and the DEF-158 anti-regression test explicitly validates the qty-mismatch path is preserved.

After this session merges, the architectural property "every flatten/retry path inspects `side` before placing SELL" holds across the entire OrderManager. Session 3 is the last side-blind retry path; the closeout's claim is structurally verified by the `_oca_threading_completeness.py` regression guard.

The Pattern Symmetry Note in the close-out is genuinely useful — it accurately describes the diff and made this review substantially faster. Future maintainers reading the comments at `:3262-3266`, `:3276-3282`, and `:3367-3374` will be able to trace the architectural rationale without consulting the close-out.

---END-REVIEW---

```json:structured-verdict
{
  "session": "3",
  "verdict": "CLEAR",
  "tests_passed": 493,
  "tests_added": 5,
  "tests_deleted": 0,
  "skips_added": 0,
  "donotmodify_violations": 0,
  "ci_status": "green",
  "ci_run_id": "25035589472",
  "ci_run_url": "https://github.com/stevengizzi/argus/actions/runs/25035589472",
  "improptu_04_pattern_mirrored": true,
  "all_branches_clear_flatten_pending": true,
  "def158_anti_regression_pass": true,
  "phantom_short_retry_blocked_severity": "critical",
  "phantom_short_retry_blocked_distinct_alert_type": true,
  "scope_compliance": "in_scope",
  "concerns": [],
  "regression_invariants_pass": [1, 2, 3, 5, 8, 9, 10, 11, 12, 14, 15, 21],
  "regression_invariants_na": [4, 6, 7, 13, 16, 17, 18, 19, 20, 22],
  "regression_invariants_fail": [],
  "escalation_criteria_triggered": []
}
```
