# Sprint 31.91 — Session 1c Tier 2 Review (Backend Safety)

**Reviewer mode:** Read-only (per RULE-013).
**Diff:** `git diff HEAD~1` against commit `49beae2` (`feat(order-manager): broker-only paths cancel-before-SELL safety — Sprint 31.91 S1c`).
**Date:** 2026-04-27.
**Gate:** This is the LAST session before Tier 3 architectural review #1 fires per `escalation-criteria.md` §A1 (combined diff: Sessions 0+1a+1b+1c).

---

---BEGIN-REVIEW---

## Verdict

**CLEAR.**

Session 1c implements broker-only paths cancel-before-SELL safety + the
`reconstruct_from_broker()` STARTUP-ONLY contract docstring exactly to spec.
All 10 session-specific review-focus items pass. All 22 sprint-level regression
invariants either pass or are N/A for this session. The do-not-modify list is
zero-edit clean. The full pytest suite reports 5,128 passed (sprint-side) +
39 pass / 5 skip (test_main.py) = 5,167 total — well above the 5,080 baseline,
fully additive (RULE-019 monotonically non-decreasing).

---

## Session-Specific Review Focus (10 items)

### 1. Cancel-before-SELL ordering — PASS

For each of the three functions, `cancel_all_orders(...)` appears textually
BEFORE `place_order(...)` (or before wiring in `reconstruct_from_broker`):

- `_flatten_unknown_position`: cancel at `order_manager.py:2067-2069`,
  SELL `place_order` at `:2097`. Cancel runs first.
- `_drain_startup_flatten_queue`: cancel at `:2215-2217`, SELL `place_order`
  at `:2249`. Cancel runs first.
- `reconstruct_from_broker`: cancel at `:1958-1960`, then `continue` on timeout
  (skip wiring); on success, the wiring path at `:1962-1991` proceeds. Cancel
  runs before any `_managed_positions[symbol] = ...` mutation.

Tests 1, 2, 3 (`test_flatten_unknown_position_calls_cancel_all_orders_first`,
`test_drain_startup_flatten_queue_calls_cancel_all_orders_first`,
`test_reconstruct_from_broker_calls_cancel_all_orders_per_symbol`) explicitly
assert this ordering via `mock_calls` index comparison and would fail if
reversed. All pass.

### 2. `await_propagation=True` everywhere — PASS

Grep confirms all 3 call sites use `await_propagation=True` as a keyword
argument:

```
self._broker.cancel_all_orders(symbol=symbol, await_propagation=True)
```

at lines 1958, 2067, and 2215. The default `False` (DEC-364 / Session 0)
is not used in production code. Tests 1, 2, 3 also assert
`c.kwargs["await_propagation"] is True` for each invocation.

### 3. `CancelPropagationTimeout` handling — PASS

For each of the 3 functions:

| Function | Exception caught? | SELL/wiring aborted? | `SystemAlertEvent` emitted? | Loop continues? |
|---|---|---|---|---|
| `_flatten_unknown_position` | YES (`:2070`) | YES (`return`) | YES via `_emit_cancel_propagation_timeout_alert(stage="eod_pass2")` | N/A — no loop |
| `_drain_startup_flatten_queue` | YES (`:2218`) | YES (`continue`) | YES via helper (`stage="startup_zombie_flatten"`) | YES (`continue`) |
| `reconstruct_from_broker` | YES (`:1968`) | YES (`continue`) | YES via helper (`stage="reconstruct_from_broker"`) | YES (`continue`) |

The shared `_emit_cancel_propagation_timeout_alert()` helper at
`:2114-2152` publishes `SystemAlertEvent(alert_type="cancel_propagation_timeout",
severity="critical", source=<call-site>, message=<symbol+shares+stage encoded>)`.

The helper's own `try / except Exception` defends against a publish failure
becoming a cascading crash (`# pragma: no cover - defensive`). This is
appropriate for a hot-path safety alert.

### 4. Reconstruct docstring is verbatim — PASS

The implemented docstring at `argus/execution/order_manager.py:1861-1879`
matches `sprint-spec.md` §D4 lines 121-135 word-for-word, with the only
acceptable formatting deltas being reST-style backticks (`` ``cancel_all_orders`` ``)
in place of Markdown backticks (since this is a Python docstring). The
Sprint 31.93 (DEF-194/195/196 reconnect-recovery) cross-reference,
`STARTUP_FRESH` vs `RECONNECT_MID_SESSION` distinction, and "operator
daily-flatten remains the safety net" framing are all present. No
rephrasing or summarization detected.

### 5. `# OCA-EXEMPT:` markers present and well-formed — PASS

Two new markers added (5 total in file; 3 are pre-existing from Session 1b):

- `:2094-2099` (`_flatten_unknown_position`): explicit reason —
  "broker-only path (no ManagedPosition exists for the unknown/zombie
  symbol). Safety comes from the `cancel_all_orders(symbol,
  await_propagation=True)` call immediately above (Sprint 31.91 Session 1c)
  which clears stale yesterday's OCA-group siblings before this SELL".
- `:2242-2247` (`_drain_startup_flatten_queue`): same shape, plus
  "queued startup zombies" wording.

Both link to the cancel-before-SELL safety mechanism and Sprint 31.91 Session 1c.
A future reviewer scanning for `# OCA-EXEMPT:` will immediately see why each
exemption is safe. The Session 1b grep regression guard
`test_no_sell_without_oca_when_managed_position_has_oca` recognizes both new
markers (verified by running the guard — passes).

### 6. Test 7 failure-mode coverage — PASS

`test_eod_pass2_cancel_timeout_aborts_sell_emits_alert_no_phantom_short`
(`tests/execution/test_broker_only_paths_safety.py:389-457`) exercises:

- `Position(side=OrderSide.BUY, shares=100)` — a long zombie (NOT a short).
  The "phantom short" the test name references is the failure mode that
  the abort PREVENTS, not what the test seeds.
- `cancel_all_orders` raises `CancelPropagationTimeout`.
- `place_order` is **NOT** called for `PHANTOM` (asserted via filtering
  `place_order.call_args_list` for `PHANTOM` symbol).
- Position is **NOT** marked closed in `_managed_positions` — explicit
  assertion `"PHANTOM" not in om._managed_positions`.
- Docstring at `:392-400` cross-references PHASE-D-OPEN-ITEMS.md Item 2
  + sprint-spec.md §D4 + the implementation prompt's Failure Mode section.
- Body comment at `:401-403` reiterates the trade-off rationale ("phantom-short
  avoidance is the entire point").

### 7. Mock fixture update is scoped — PASS

12 test files modified; each modification is a single-line addition of
`cancel_all_orders = AsyncMock(return_value=0)` next to existing
`cancel_order` mocks (or in inline `MagicMock()` test bodies):

- `tests/execution/order_manager/test_core.py` (+59 — but 12 separate
  fixture sites, each a single line; total file size +59 reflects the
  multiple `mock_broker = MagicMock()` inline test bodies)
- 10 sibling order-manager test files (+1 each)
- `tests/integration/historical/test_integration_sprint5.py` (+1)

Verified via `git diff` per file: zero existing fixture behavior modified;
zero tests deleted/skipped. RULE-019 honored (pytest pass count goes 4862
scoped pre-session → 462 scoped post-session = +7 new tests; full suite
goes from baseline ~5121 to 5128 = +7).

The reason this update was necessary (and is "scoped"): Session 0 added
`cancel_all_orders` to the Broker ABC; Session 1c is the first session to
invoke it on broker-only paths in OrderManager production code, so any
broker mock that previously used `MagicMock()` (which raises `TypeError:
object MagicMock can't be used in 'await' expression`) needed an explicit
AsyncMock. The closeout's §7 documents this discovery accurately.

### 8. Sprint 31.93 cross-reference present — PASS

The reconstruct docstring contains the verbatim phrase:

> "Sprint 31.93 (DEF-194/195/196 reconnect-recovery) is the natural sprint
> to add this differentiation."

Matches sprint-spec.md §D4 line 133. Cross-reference is structurally bound
(identifier + DEF numbers + sprint description), making future search
across decision-log + sprint-history reliable.

### 9. DEF-199 A1 fix unchanged — PASS

`git diff HEAD~1 -- argus/execution/order_manager.py` shows the first
hunk starts at line 1858 (`reconstruct_from_broker`); the DEF-199 A1 fix
region at lines 1670-1750 has zero edits. Verified by reading the
current state of `:1670-1750` — all of: EOD Pass 1 retry side-check at
`:1715-1743`, EOD Pass 2 side-check at `:1764+`, both 3-branch BUY/SELL/None
patterns are intact.

`tests/execution/order_manager/test_def199_eod_short_flip.py` — all 6
tests pass (4 Pass-2 side-check tests + 2 Pass-1 retry side-check tests).

`test_eod_pass2_stale_oca_cleared_before_sell` (the new test 4) also
passes alongside, confirming the cancel-before-SELL gate composes
correctly with the existing Pass 2 short-detection logic.

### 10. Session 1b grep regression guard still green — PASS

`tests/_regression_guards/test_oca_threading_completeness.py` — all 4 tests
pass (the main `test_no_sell_without_oca_when_managed_position_has_oca` plus
3 marker-recognition self-tests). The two new `# OCA-EXEMPT:` markers added
in Session 1c are tolerated within the 30-line lookback window of the new
SELL placements at `_flatten_unknown_position:2097` and
`_drain_startup_flatten_queue:2249`.

`tests/_regression_guards/test_oca_simulated_broker_tautology.py` (Invariant 21)
also passes — Session 1c did not add any SimulatedBroker-based OCA assertions.

---

## Sprint-Level Regression Checklist (22 invariants)

| # | Invariant | Status | Notes |
|---|---|---|---|
| 1 | DEF-199 A1 fix detects + refuses 100% of phantom shorts at EOD | PASS | `git diff` clean on `:1670-1750`; all 6 test_def199 tests pass. |
| 2 | DEF-199 A1 EOD Pass 1 retry side check | PASS | `test_pass1_retry_skips_short_position` passes. |
| 3 | DEF-158 dup-SELL prevention works for ARGUS=N, IBKR=N | PASS | `_check_flatten_pending_timeouts` not modified; test_def158.py unchanged behaviorally. |
| 4 | DEC-117 atomic bracket invariant | PASS | `ibkr_broker.py` zero diff. |
| 5 | 5,080 pytest baseline holds | PASS | Full suite: 5128 passed; +7 new tests this session, monotonic. |
| 6 | `tests/test_main.py` baseline 39 pass + 5 skip | PASS | Verified directly: `39 passed, 5 skipped in 4.42s`. |
| 7 | Vitest baseline holds at 866 | N/A | Backend-only session; not exercised. |
| 8 | Risk Manager check 0 unchanged | PASS | `argus/core/risk_manager.py` zero diff. |
| 9 | IMPROMPTU-04 startup invariant unchanged | PASS | `argus/main.py` zero diff. |
| 10 | DEC-367 margin circuit breaker unchanged | PASS | No edits to circuit-breaker code. |
| 11 | Sprint 29.5 EOD flatten circuit breaker unchanged | PASS | EOD circuit logic preserved. |
| 12 | Pre-existing flakes did not regress | PASS | Full suite green; standard "Task was destroyed" warnings consistent with baseline; no new DEFs needed. |
| 13 | New config fields parse without warnings | N/A | Session 1c adds no new YAML fields. |
| 14 | Monotonic-safety property (after-Session-1c row) | PASS | Row "After Session 1c": OCA bracket=YES, OCA standalone (4)=YES, Broker-only safety=YES, Restart safety=YES, all others=NO. Aligns with embedded matrix. |
| 15 | No items on do-not-modify list touched | PASS | All 9 do-not-modify items zero-diff. The scoped exception (reconstruct_from_broker body in order_manager.py) is documented per invariant 15's Session 1c carve-out. |
| 16 | Bracket placement performance | N/A | Session 4 wires this into debrief; observational only here. |
| 17 | Mass-balance assertion at session debrief | N/A | Session 4 delivers; not yet active. |
| 18 | Alert observability — banner cross-page | N/A | Session 5e delivers. |
| 19 | Alert observability — WS reconnect resilience | N/A | Sessions 5a.2 / 5c deliver. |
| 20 | Acknowledgment audit-log persistence | N/A | Session 5a.1 / 5a.2 deliver. |
| 21 | SimulatedBroker OCA-assertion tautology guard | PASS | `test_no_oca_assertion_uses_simulated_broker` passes. |
| 22 | Spike script freshness | N/A | Lands at Session 4. |

---

## Sprint-Level Escalation Criteria (Session 1c relevance)

| # | Trigger | Status | Notes |
|---|---|---|---|
| A1 | Session 1c lands cleanly + Tier 2 CLEAR → fires Tier 3 #1 | **READY TO FIRE** | Verdict CLEAR; operator can now arrange Tier 3 architectural review #1 (combined diff Sessions 0+1a+1b+1c). |
| A2 | Tier 2 CONCERNS or ESCALATE | NOT TRIGGERED | Verdict CLEAR. |
| A3 | Post-merge paper session shows phantom-short accumulation | N/A | Pre-merge review; verification is post-merge. |
| A8 | Bracket placement performance regression | N/A | Session 4 measurement window. |
| B1 | Pre-existing flake count increases | NOT TRIGGERED | Full suite green; no new DEF needed. |
| B3 | Pytest baseline ends below 5,080 | NOT TRIGGERED | 5128 ≥ 5080. |
| B4 | CI fails on session's final commit | UNVERIFIED FROM REVIEW | Local pytest is green; reviewer notes that operator must confirm CI green per RULE-050 before Tier 3 #1 fires. (Not blocking for this verdict; standard sprint protocol.) |
| B5 | DISCOVERY line numbers drift > 5 lines | NOT TRIGGERED | Diff hunks at `:1858, :1946, :2055, :2092, :2111, :2205, :2240` — within tolerance of the impl prompt's `:1813, :1920, :2021` references after Session 1b's recent landing pushed lines down. (Closeout §1 cites the actual landed line numbers.) |
| B6 | A do-not-modify-list file appears in `git diff` | NOT TRIGGERED | All 9 protected paths zero-diff. |
| C5 | Uncertainty about do-not-modify boundary | NOT TRIGGERED | Closeout explicitly verifies main.py:1081 zero-diff. |

---

## Notes on Closeout's Discovered Edge Cases (§7)

Three edge cases noted by implementer; all appropriately handled:

1. **Mock fixture incompleteness across 12 test files** — explained accurately;
   the fix is the minimal one-liner `cancel_all_orders = AsyncMock(return_value=0)`;
   no existing tests deleted/skipped. RULE-019 honored.

2. **`ManagedPosition._broker_confirmed` is set on entry-fill, not in
   `reconstruct_from_broker`** — implementer correctly identifies the spec's
   "wired with `_broker_confirmed=True`" claim as forward-looking
   (Session 2b.1 invariant extension), not a Session 1c assertion. Test 3
   asserts the wiring success condition that IS testable today
   (`symbol in om._managed_positions`). This is correct framing.

3. **`SystemAlertEvent` does not carry a structured `metadata` dict** — the
   implementation prompt's `metadata=...` example was suggestive, not
   normative. Implementer encoded `symbol`, `shares`, `stage` into the
   formatted `message` string + `source` field. Tests assert on
   `alert_type`, `severity`, and message-substring (`"PHANTOM" in
   alert.message`). This is a sufficient operational signal; adding a
   structured `metadata` field would be a separate, additive API change.

   **Note for Tier 3 reviewer:** if the alert observability sprint
   (5a.1+5a.2+5b) introduces a structured-metadata requirement, the encoding
   choice here is forward-compatible — message-string parsing remains a
   safe fallback while a dedicated `metadata: dict[str, Any]` field gets
   added to `SystemAlertEvent`. No deferred-item filing required at this
   stage.

---

## Cleanliness checks

- **Imports added correctly:** `SystemAlertEvent` from `argus.core.events`
  and `CancelPropagationTimeout` from `argus.execution.broker`. Both are
  necessary; both are correctly placed in alphabetical groups.
- **Helper extraction is clean:** `_emit_cancel_propagation_timeout_alert`
  is a single shared helper for the 3 emission sites (DRY); accepts
  keyword-only args (`*`); has a docstring; defensively wraps `publish` in
  `try / except Exception` with `# pragma: no cover - defensive` annotation.
- **Comments on the cancel-before-SELL gates** are substantive and link
  to PHASE-D-OPEN-ITEMS Item 2, sprint-spec.md §D4, and the cancel-then-SELL
  rationale. A future maintainer reading the code will understand why
  the gate exists.
- **No magic strings:** alert type `"cancel_propagation_timeout"` and
  severity `"critical"` are consistent across all 3 emission sites via
  the shared helper. (If a future sprint adds a constants module for
  alert types, the consolidation point is the helper, not 3 separate sites.)

---

## Tier 3 Readiness Note

Session 1c's closeout §10 anticipates the 4 most likely Tier 3 architectural
questions (DEC-117 interaction; new failure mode bounded?; runtime check vs
docstring; OCA-EXEMPT mechanism robustness) with substantive answers. The
combined-diff scope for Tier 3 #1 (Sessions 0+1a+1b+1c) is internally
consistent: the OCA architecture as-of-end-of-Session-1c is a complete
4-layer stack (API contract / bracket OCA / standalone-SELL OCA / broker-only
safety), each layer testable in isolation and verifiable in combination.

The reviewer's recommendation to Tier 3: focus the architectural review on
(a) the **leaked-long failure mode** (the new bounded-exposure trade-off),
(b) the **`reconstruct_from_broker` STARTUP-ONLY contract enforcement
mechanism** (docstring vs runtime gate), and (c) the **OCA-EXEMPT marker
discipline** (whether the grep guard is sufficient enforcement long-term
or whether structural typing — e.g., a `BrokerOnlySell` marker class — would
be a cleaner future evolution).

These are not blocking concerns; they are the natural Tier 3 questions
given the architecture's shape after Session 1c.

---

## Recommendation

**Verdict: CLEAR.** Session 1c is ready to merge to `main`. Operator may
proceed to fire Tier 3 architectural review #1 per `escalation-criteria.md`
§A1 once CI confirms green on commit `49beae2`.

---END-REVIEW---

```json:structured-verdict
{
  "session": "1c",
  "verdict": "CLEAR",
  "tier_3_readiness": "READY",
  "do_not_modify_violations": 0,
  "tests_added_this_session": 7,
  "tests_total_post_session": 5167,
  "regression_invariants_pass": [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15, 21],
  "regression_invariants_na": [7, 13, 16, 17, 18, 19, 20, 22],
  "escalation_triggers_active": ["A1"],
  "escalation_triggers_not_triggered": ["A2", "A3", "A8", "B1", "B3", "B4_local_only", "B5", "B6", "C5"],
  "post_review_fixes_required": false,
  "ci_status_remark": "Local pytest green; operator must verify CI green on 49beae2 before Tier 3 #1 fires (RULE-050)."
}
```
