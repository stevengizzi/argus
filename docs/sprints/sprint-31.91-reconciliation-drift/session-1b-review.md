# Sprint 31.91 Session 1b — Tier 2 Review

**Reviewer:** Backend safety reviewer (Tier 2, @reviewer subagent)
**Session:** 1b — Standalone-SELL OCA threading + Error 201 graceful handling (D3)
**Commit under review:** `6009397` on `main` (single commit; `git diff HEAD~1`)
**Review scope:** READ-ONLY, no source files modified.

---BEGIN-REVIEW---

## Summary

Session 1b implements D3 (standalone-SELL OCA threading + Error 201 graceful
handling) with a high-quality, well-scoped surgical edit confined to
`argus/execution/order_manager.py` plus two new test files. All four threaded
paths fire correctly, all five OCA-EXEMPT sites are well-justified, the
DEF-199 A1 fix and DEF-158 dup-SELL prevention are preserved, and the grep
regression guard is sound. The five Judgment Calls are reasonable and
surfaced honestly. Two minor concerns identified — both are
documentation/counting accuracy issues, not safety issues.

## Verdict

**CLEAR.** All safety-critical invariants hold. Both concerns are minor and
do not block progression.

## Diff Inspection

`git diff HEAD~1 --name-only` returns exactly 5 files:
- `argus/execution/order_manager.py` (+184 / -11 net)
- `docs/sprints/sprint-31.91-reconciliation-drift/session-1b-closeout.md`
- `docs/sprints/sprint-31.91-reconciliation-drift/session-1b-staged-flow-report.md`
- `tests/_regression_guards/test_oca_threading_completeness.py` (new, 191 lines)
- `tests/execution/test_standalone_sell_oca_threading.py` (new, 515 lines)

`git diff HEAD~1 --` over the do-not-modify list returns **zero lines**:
`argus/main.py`, `argus/models/trading.py`, `argus/execution/alpaca_broker.py`,
`argus/data/alpaca_data_service.py`, `argus/execution/ibkr_broker.py`,
`docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`, `workflow/`. Compliance: PASS.

`git diff HEAD~1 -- argus/core/risk_manager.py` returns zero lines (Invariant 8). PASS.

Hunk start lines in `order_manager.py`: 55, 65, 122, 1987, 2063, 2212, 2229,
2241, 2270, 2300, 2437, 2510, 2531, 2607, 2624, 2699, 2722. **No hunks within
DEF-199 A1 range (1670-1750).** The A1 fix block at current lines 1698-1779
(post-edit positions) is structurally intact and preserves all three branches
(BUY/flatten, SELL/error+skip, unknown/error+skip) for both Pass 1 retry and
Pass 2.

## Test Results

| Test invocation | Result |
|---|---|
| `python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q` | 455 passed, 2 warnings, 8.18s |
| `python -m pytest --ignore=tests/test_main.py -n auto -q` | 5,121 passed, 27 warnings, 61.66s |
| `python -m pytest tests/test_main.py -q` | 39 passed, 5 skipped, 4.09s |
| `tests/execution/test_standalone_sell_oca_threading.py` | 11/11 PASSED |
| `tests/_regression_guards/test_oca_threading_completeness.py` | 4/4 PASSED |
| `tests/execution/order_manager/test_def199_eod_short_flip.py` | 6/6 PASSED |
| `tests/execution/order_manager/test_def158.py` | 5/5 PASSED |
| `tests/_regression_guards/test_oca_simulated_broker_tautology.py` | 1/1 PASSED |

5,121 ≥ 5,080 baseline (Invariant 5 holds). 39+5 baseline holds (Invariant 6).

## Focus Points

### 1. All 4 paths thread OCA correctly

**PASS.** All four required threading sites verified by code inspection AND
by the four `TestThreadingPerPath` tests:
- `_submit_stop_order` at line 2326-2329 (covers `_resubmit_stop_with_retry`
  per Judgment Call 1)
- `_trail_flatten` at line 2641-2644
- `_escalation_update_stop` at line 2754-2757
- `_flatten_position` at line 2862-2865

Each pattern: `if position.oca_group_id is not None: order.ocaGroup =
position.oca_group_id; order.ocaType = _OCA_TYPE_BRACKET`. The
`_OCA_TYPE_BRACKET = 1` module constant is defined at line 81 with thorough
lock-step rationale comments.

### 2. Error 201 distinguishing logic

**PASS.** All four call sites use the imported helper
`_is_oca_already_filled_error` (from `argus.execution.ibkr_broker`, NOT
duplicated; import at line 58). Each site:
- OCA-filled path → `_handle_oca_already_filled(position, where=...)` returns
  immediately. Helper sets `redundant_exit_observed = True` and emits a
  single INFO log line. **Crucially, the helper does NOT touch
  `_flatten_pending`** — the DEF-158 retry short-circuit invariant.
- Generic exception path → existing behavior preserved (retry loop in
  `_submit_stop_order`; CRITICAL log + return in `_trail_flatten`;
  `_flatten_position(reason="escalation_failure")` cascade in
  `_escalation_update_stop`; CRITICAL log in `_flatten_position`).

In `_flatten_position` specifically: the OCA-filled exception is caught
BEFORE `self._flatten_pending[symbol]` would be assigned (the assignment is
after `place_order` returns, inside the same try-block, so an exception from
`place_order` skips the assignment). Verified.

### 3. DEF-199 A1 fix anti-regression

**PASS.** `git diff HEAD~1 -- argus/execution/order_manager.py` shows zero
hunks within the 1670-1750 range. All 6 tests in `test_def199_eod_short_flip.py`
pass:
- `test_short_position_is_not_flattened_by_pass2`
- `test_long_position_is_still_flattened_by_pass2`
- `test_mixed_long_and_short_at_pass2_only_long_flattened`
- `test_pass2_position_with_side_none_is_skipped`
- `test_pass1_retry_skips_short_position`
- `test_pass1_retry_still_flattens_long_timeout`

Invariant 1 and Invariant 2 PASS.

### 4. DEF-158 dup-SELL prevention preserved

**PASS.** `_check_flatten_pending_timeouts` body is unchanged — the diff at
that location adds only an OCA-EXEMPT comment block (no functional change).
All 5 tests in `test_def158.py` pass:
- `test_flatten_timeout_skips_resubmit_when_broker_position_closed`
- `test_flatten_timeout_does_resubmit_when_broker_position_exists`
- `test_startup_cleanup_cancels_existing_orders_before_flatten`
- `test_stop_fill_cancels_concurrent_flatten_order`
- `test_flatten_fill_cancels_other_pending_flatten_orders`

Invariant 3 PASS.

### 5. Grep regression guard correctness

**PASS.** The implementation deviates from the spec's literal regex (which
doesn't match ARGUS's actual code shape — `Order(...)` constructed separately
from `_broker.place_order(order)`), but this is documented in three places
(test docstring, close-out Judgment Call 3, staged-flow report). The semantic
intent — "every SELL placement either threads OCA or is explicitly exempt" —
is preserved.

The guard correctly identifies all 9 `_broker.place_order` sites: 4 are
threaded (OCA-marker found in window), 5 are OCA-EXEMPT (comment found).
Three companion tests (negative-case + 2 positive-case) verify the guard
logic. The 30-line window is reasonable.

A minor robustness observation: the guard scans ALL `_broker.place_order`
calls (not just SELL); BUY orders (none currently) would also need either
threading or an exemption comment. This is acceptable since BUY orders are
conceptually exempt, and adding `# OCA-EXEMPT: BUY entry` is a trivial future
remedy if needed.

### 6. Race window correctness

**PASS.** `test_race_window_two_paths_same_oca_group` verifies that
`_trail_flatten` and `_escalation_update_stop` firing on the same position
both stamp the same `ocaGroup` value and `ocaType=1`. The IBKR-side atomic
cancellation is verified separately by the spike script (out of scope for
unit tests, per Sprint Spec).

### 7. `_flatten_position` central-path coverage

**PASS.** All 4+ upstream callers benefit from OCA threading "for free":
- EOD Pass 1 callers (`order_manager.py:1670`, `:806`, `:832`, `:1160`)
- `close_position()` API (line ~1854 via `emergency_flatten`)
- `time_stop` exits (lines 1569, 1592)
- `bracket_exhausted` (line 729)
- `t2_target` (line 806)
- `stop_retry_exhausted` (line 832)
- `bracket_amendment_safety` (line 1160)
- `stop_order_failure` from `_submit_stop_order` cascade (line 2363)
- `escalation_failure` from `_escalation_update_stop` cascade (line 2791)

The threading evidence is on the placed `Order` object passed to
`place_order(order)`, observable via the broker mock's `call_args_list`. All
four upstream-caller scenarios are implicitly covered by
`test_flatten_position_threads_oca_group`.

## Sprint-Level Regression Checklist (22 invariants)

| # | Invariant | Result |
|---|-----------|--------|
| 1 | DEF-199 A1 fix detects + refuses 100% phantom shorts at EOD | PASS |
| 2 | DEF-199 A1 EOD Pass 1 retry respects side check | PASS |
| 3 | DEF-158 dup-SELL prevention works for ARGUS=N, IBKR=N | PASS |
| 4 | DEC-117 atomic bracket invariant: parent fails → all children cancelled | N/A (Session 1a scope; verified zero edits to ibkr_broker.py) |
| 5 | 5,080 pytest baseline holds; new tests additive | PASS (5,121 ≥ 5,080) |
| 6 | `tests/test_main.py` baseline holds (39 + 5 skip) | PASS |
| 7 | Vitest baseline at 866 unchanged | N/A (backend session, Vitest not exercised) |
| 8 | Risk Manager check 0 unchanged | PASS (zero edits) |
| 9 | IMPROMPTU-04 startup invariant unchanged | PASS (zero edits to main.py) |
| 10 | DEC-367 margin circuit breaker unchanged | PASS |
| 11 | Sprint 29.5 EOD flatten circuit breaker unchanged | PASS |
| 12 | Pre-existing flakes did not regress | PARTIAL — pre-existing "Task was destroyed but it is pending" warnings reproduced in scoped run; per RULE-050 CI run is pending push |
| 13 | New config fields parse without warnings | N/A (Session 1b adds no config fields) |
| 14 | Monotonic-safety property — Row "After Session 1b" | PASS (OCA bracket=YES, OCA standalone=YES, others=NO) |
| 15 | Do-not-modify list untouched | PASS (verified via `git diff` over all listed files) |
| 16 | Bracket placement performance does not regress | N/A (Session 4 scope) |
| 17 | Mass-balance assertion at session debrief | N/A (Session 4 scope) |
| 18 | Alert observability — banner cross-page persistence | N/A (Session 5e scope) |
| 19 | Alert observability — WebSocket reconnect resilience | N/A (Session 5c scope) |
| 20 | Alert observability — acknowledgment audit-log persistence | N/A (Session 5a.1/5a.2 scope) |
| 21 | SimulatedBroker OCA-assertion tautology guard | PASS (collateral fix in Judgment Call 5; tautology guard re-runs green) |
| 22 | Spike script freshness | N/A (Session 4 scope) |

## Judgment Call Review

**JC1 (threading at `_submit_stop_order` instead of `_resubmit_stop_with_retry`):**
Reasonable. `_resubmit_stop_with_retry` does not directly call
`_broker.place_order` — it delegates to `_submit_stop_order`. Threading at the
actual placement site covers the spec's stated intent (DEC-372 retry path)
AND covers 3 other callers (`_handle_revision_rejected`,
`_amend_bracket_on_slippage`, stop-to-breakeven). The grep regression guard
correctly mandates threading at the placement site. Architecturally correct.

**JC2 (`_OCA_TYPE_BRACKET = 1` as module constant):** Reasonable given the
constraint. `OrderManager` does not have access to `IBKRConfig` (different
config tree), and the constraint forbids modifying `argus/main.py`. The
lock-step concern (if operator flips `IBKRConfig.bracket_oca_type` from 1 to
0, this constant must be updated in lock-step) is well-documented in the
constant's docstring AND surfaced as Follow-Up #1 for `live-operations.md`
doc sync. Note: a latent inconsistency exists under the rollback flag — if
`bracket_oca_type=0`, brackets still record an `oca_group_id` but with
`ocaType=0`; Session 1b's standalone SELLs would still attempt OCA threading
with `ocaType=1`. This is bounded by the existing IBKRConfig
"RESTART-REQUIRED" note. Surfaced honestly.

**JC3 (Grep regex deviation from spec):** Reasonable. The spec's literal
regex `r"_broker\.place_order\([^)]*side\s*=\s*[^,)]*SELL[^)]*\)"` does not
match ARGUS's pattern of constructing the `Order` separately. The
implementation preserves intent; deviation is documented in 3 places (test
docstring, close-out, staged-flow report). Three companion tests prove the
guard fires when expected.

**JC4 (OCA-EXEMPT comments on 5 sites):** Reasonable. Pre-flight grep found 9
total `_broker.place_order` sites: 4 in-scope + 5 explicitly out-of-scope.
The "halt if more than 4" criterion was for new SELL paths, not pre-existing
ones. Each exemption carries a clear cross-reference to the responsible
session/scope. C7 escalation criterion correctly applied.

**JC5 (Tautology guard collateral fix):** Reasonable. The new test docstring
originally referenced "SimulatedBroker"; the Invariant 21 tautology guard
would have flagged that. Rephrased docstring to avoid the literal string
while preserving substantive guidance via cross-reference. Tautology guard
re-runs green (verified).

## Concerns

### Minor concern 1 — Test count discrepancy in close-out

The close-out reports `delta_pytest: +16 (12 standalone-sell OCA threading +
4 grep regression guard)`. Actual count: **11** standalone tests + 4 grep
guard tests = **15** new tests, not 16.

`pytest --collect-only` confirms 11 tests in
`test_standalone_sell_oca_threading.py`:
- TestThreadingPerPath (4)
- TestFallthroughWhenNone (1)
- TestRaceWindowSameOcaGroup (1)
- TestError201OcaFilledHandling (5)
- Total: 11

The full-suite figure of 5,121 was verified end-to-end and exceeds the 5,080
baseline by 41 (consistent with prior baseline drift the close-out itself
acknowledges: "5,080 → 5,096 expected; observed 5,121 — the additional 25
over expected reflect post-CLAUDE.md baseline drift, not Session-1b-introduced
tests"). The miscount is in the per-file breakdown only. Not a safety issue.

### Minor concern 2 — CI run not yet executed (RULE-050)

The close-out's Self-Assessment marks `[ ] CI green — pending push (operator
action)`. Commit `6009397` has not been pushed; no CI run exists for it.
RULE-050 requires green CI before next session.

This is **explicitly acknowledged** by the implementer (not hidden). The
close-out documents the procedural gap and identifies the operator action
needed. Local full suite (5,121 passed) and scoped suite (455 passed) both
green. I treat this as a procedural pending step (which the operator must
execute before declaring Session 1b complete), not as a verdict-altering
issue. CLEAR with explicit operator action required: push and verify CI
green before starting Session 1c.

## Strengths to acknowledge

1. **Surgical edit discipline.** All production changes confined to a single
   file; no drive-by refactors.
2. **Exemplary documentation.** Each addition cites Sprint/Session/DEC
   anchors. Each judgment call surfaces the deviation rationale.
3. **Honest deviation surfacing.** Five judgment calls all surfaced clearly
   with reasoning. The grep-guard deviation is documented in 3 places (test,
   close-out, staged-flow report) — an excellent pattern.
4. **Correct DEF-158 short-circuit semantics.** The `_handle_oca_already_filled`
   helper deliberately avoids touching `_flatten_pending`, preserving the
   dup-SELL prevention invariant and short-circuiting the retry path cleanly.
5. **Helper reuse, not duplication.** `_is_oca_already_filled_error` imported
   from `ibkr_broker` (line 58) — exactly per spec.
6. **Strong regression guards.** New `test_oca_threading_completeness.py`
   adds a self-validating grep guard (4 tests including negative + positive
   cases proving the guard works). This catches future regressions where
   someone adds a SELL path without OCA threading.

## Recommended Operator Actions

1. **Push commit `6009397` to origin/main** and verify CI green per RULE-050.
2. **Doc sync (Follow-Up #1):** add a paragraph to `live-operations.md`
   runbook noting that `_OCA_TYPE_BRACKET` in `order_manager.py` must be
   updated in lock-step with any flip of `IBKRConfig.bracket_oca_type`.
3. **Update test count in close-out (cosmetic):** change `+16 (12
   standalone-sell OCA threading + 4 grep regression guard)` to `+15 (11
   standalone-sell OCA threading + 4 grep regression guard)`. Not a blocker.

---END-REVIEW---

```json
{
  "session": "1b",
  "sprint": "31.91-reconciliation-drift",
  "deliverable": "D3",
  "verdict": "CLEAR",
  "scope_compliance": "PASS",
  "do_not_modify_list_compliance": "PASS",
  "tests": {
    "scoped": "455 passed (tests/execution/ + tests/_regression_guards/)",
    "full": "5,121 passed (--ignore=tests/test_main.py -n auto -q)",
    "test_main": "39 passed, 5 skipped",
    "baseline_holds": true,
    "new_tests_added": 15,
    "new_tests_in_close_out": 16,
    "test_count_discrepancy_noted": "Off by 1 (close-out says 12 standalone, actual 11)"
  },
  "invariants_pass": [1, 2, 3, 5, 6, 8, 9, 10, 11, 14, 15, 21],
  "invariants_na_for_session": [4, 7, 13, 16, 17, 18, 19, 20, 22],
  "invariants_partial": [12],
  "concerns": [
    {
      "severity": "minor",
      "category": "documentation",
      "description": "Close-out reports +16 new tests; actual is +15 (off-by-one in standalone test file count). Total suite count (5,121) verified end-to-end."
    },
    {
      "severity": "procedural",
      "category": "RULE-050",
      "description": "Commit 6009397 not yet pushed to origin; no CI run for the session. Close-out explicitly acknowledges this as a pending operator action. Local full suite verified green."
    }
  ],
  "judgment_calls_reasonable": true,
  "judgment_calls_surfaced": true,
  "context_state": "GREEN",
  "operator_actions_required": [
    "Push commit 6009397 and verify CI green before starting Session 1c (RULE-050).",
    "Doc-sync follow-up: add live-operations.md paragraph on _OCA_TYPE_BRACKET lock-step constraint with IBKRConfig.bracket_oca_type."
  ],
  "ready_for_next_session": true,
  "next_session": "1c"
}
```
