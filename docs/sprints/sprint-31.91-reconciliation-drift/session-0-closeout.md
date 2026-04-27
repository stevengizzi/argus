# Sprint 31.91 — Session 0 Close-Out

```markdown
---BEGIN-CLOSE-OUT---

**Session:** Sprint 31.91 — Session 0: `Broker.cancel_all_orders(symbol, await_propagation)` API Extension
**Date:** 2026-04-27
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/execution/broker.py` | modified | Added `CancelPropagationTimeout` exception class; extended `Broker.cancel_all_orders` ABC signature with `symbol: str \| None = None, *, await_propagation: bool = False`. |
| `argus/execution/ibkr_broker.py` | modified | Implemented `symbol` filter via `trade.contract.symbol` on `self._ib.openTrades()` cache; added `await_propagation=True` polling loop (100 ms interval, 2 s budget) raising `CancelPropagationTimeout`; preserved DEC-364 no-args `reqGlobalCancel` path verbatim. Added `CancelPropagationTimeout` import. |
| `argus/execution/simulated_broker.py` | modified | Added `symbol` filter on `_pending_brackets` list; `await_propagation=True` is a no-op (cancellation is synchronous in-memory). DEC-364 no-args path preserved exactly. |
| `argus/execution/alpaca_broker.py` | modified | Renamed existing impl to `_cancel_all_orders_legacy` (body untouched per prompt); added new ABC-compliant `cancel_all_orders` that emits `DeprecationWarning` (naming Sprint 31.94 as the retirement target) and delegates to the legacy method. Symbol filter / `await_propagation` deliberately not implemented per L1 disposition. |
| `tests/execution/test_cancel_all_orders_extension.py` | added | 8 new pytest tests covering DEC-364 preservation, symbol filter, await_propagation polls-until-empty, await_propagation timeout, AlpacaBroker DeprecationWarning, IBKR filter source verification, plus 2 regressions on SimulatedBroker (symbol-filter + no-args). |

### Judgment Calls
Decisions made during implementation that were NOT specified in the prompt:
- **AlpacaBroker latent pre-existing bug (`_check_connected` does not exist on `AlpacaBroker`).** The pre-existing legacy body calls `self._check_connected()` (line 799 post-rename), but `_check_connected` is only defined on `SimulatedBroker`. This is a latent AttributeError on first invocation. The prompt explicitly forbade touching the legacy function's body ("DO NOT touch the legacy function's body"); per RULE-001 (execute exactly what the prompt specifies) and the spec-by-contradiction's #5 disposition (AlpacaBroker queued for retirement in Sprint 31.94, no business-logic changes), the bug is preserved as-is and surfaced here. Recorded as a deferred observation in the structured appendix.
- **Bonus 2 SimulatedBroker tests (8 total instead of the 6 the prompt called out).** The prompt enumerated 6 tests; I added 2 SimulatedBroker tests (symbol-filter and no-args clears-everything) to mirror the IBKR coverage on the second implementation, since DEC-364 preservation on `SimulatedBroker` is a separate code path from IBKR's `reqGlobalCancel`. Net delta: +8 pytest, all additive, no scope expansion.
- **No SimulatedBroker OCA-assertion tautology guard (Invariant 21).** The prompt's "Sprint-Level Regression Checklist" note says invariant 21 LANDS at Session 0 close-out OR may be deferred to Session 1a. Session 1a is where `Order.oca_group_id` arrives; Session 0 does not introduce `Order` field changes, so the assertion has no implementation surface to bind to yet. Deferring the test to Session 1a is the natural fit. Surfaced explicitly in "Notes for Reviewer" below.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| `CancelPropagationTimeout` exception in `argus/execution/broker.py` | DONE | `argus/execution/broker.py` lines 21–25 |
| Updated `Broker` ABC signature | DONE | `argus/execution/broker.py:148-176` |
| `IBKRBroker` symbol filter via `trade.contract.symbol` on `openTrades()` | DONE | `argus/execution/ibkr_broker.py:1086-1183` |
| `IBKRBroker` `await_propagation=True` polling, 100ms interval, 2s timeout | DONE | `argus/execution/ibkr_broker.py:1153-1183` |
| `IBKRBroker` raises `CancelPropagationTimeout` on timeout | DONE | `argus/execution/ibkr_broker.py:1170-1175` |
| `SimulatedBroker` symbol filter on `_pending_brackets` | DONE | `argus/execution/simulated_broker.py:629-661` |
| `SimulatedBroker` `await_propagation=True` is synchronous no-op | DONE | Comment block at `simulated_broker.py:639-643` documents semantics |
| `AlpacaBroker.cancel_all_orders` emits `DeprecationWarning` | DONE | `argus/execution/alpaca_broker.py:761-790` |
| `AlpacaBroker._cancel_all_orders_legacy` unchanged body | DONE | `argus/execution/alpaca_broker.py:792-806` (rename only) |
| DEC-364 contract preserved (no-args cancels everything) | DONE | All three impls; verified by `test_cancel_all_orders_no_args_preserves_dec364` and `test_simulated_broker_cancel_all_orders_no_args_clears_everything` |
| 6 new pytest tests | DONE (+2 bonus) | `tests/execution/test_cancel_all_orders_extension.py` — 8 tests, all passing |
| `order_manager.py` not modified | DONE | `git diff` confirms zero edits |
| `main.py` not modified | DONE | `git diff` confirms zero edits |
| `models/trading.py` not modified | DONE | `git diff` confirms zero edits |
| `alpaca_data_service.py` not modified | DONE | `git diff` confirms zero edits |
| 2s timeout inline (no config field) | DONE | Constant at `ibkr_broker.py:1154` (`timeout_seconds = 2.0`) |
| No premature wiring (caller-side) | DONE | `grep -rn 'cancel_all_orders('` shows only pre-existing call sites; all use no-args |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Existing pre-Session-0 callers of `cancel_all_orders()` (no args) still work | PASS | `grep -rn 'cancel_all_orders('` enumerates `argus/main.py:2268`, `tests/execution/order_manager/test_safety.py:367/393/995`, `tests/execution/order_manager/test_reconciliation.py:94`, `tests/execution/order_manager/test_reconciliation_redesign.py:91`. All call no-args; default `symbol=None, await_propagation=False` preserves DEC-364 behavior exactly. Full pytest run confirms zero regressions. |
| `git diff HEAD~1 -- argus/execution/order_manager.py` shows zero edits | PASS | `git diff -- argus/execution/order_manager.py \| wc -l` = 0 |
| `git diff HEAD~1 -- argus/main.py` shows zero edits | PASS | `git diff -- argus/main.py \| wc -l` = 0 |
| `git diff HEAD~1 -- argus/models/trading.py` shows zero edits | PASS | `git diff -- argus/models/trading.py \| wc -l` = 0 |
| `git diff HEAD~1 -- argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix) shows zero edits | PASS | File-level diff is 0; subsumes line range. Critical Invariant 1 preserved. |
| AlpacaBroker emits `DeprecationWarning` on call | PASS | `tests/execution/test_cancel_all_orders_extension.py::test_alpaca_broker_cancel_all_orders_raises_deprecation_warning` passes (asserts warning category + matches "Sprint 31.94" string). |
| Pre-existing flake count unchanged | PASS | Full pytest run: 5,088 passed (5,080 baseline + 8 new), 25 warnings; no test transitioned from PASS to FAIL. DEF-150/167/171/190/192 not exercised in this scope; baseline (`/tmp/baseline_pytest.txt`) and post (`/tmp/post_pytest.txt`) both finished cleanly. |
| `tests/test_main.py` baseline (39 pass + 5 skip) unchanged | PASS | `python -m pytest tests/test_main.py -q` → "39 passed, 5 skipped in 5.56s" — identical to documented baseline. |
| `git diff -- argus/data/alpaca_data_service.py` shows zero edits | PASS | 0 lines diff; alpaca_data_service.py:593 emitter TODO untouched (in-scope only for Session 5b anti-regression). |

### Test Results
- Tests run: 5,088 (`--ignore=tests/test_main.py -n auto`) + 39 + 5 skipped (`tests/test_main.py`)
- Tests passed: 5,088 + 39
- Tests failed: 0
- New tests added: 8 (file: `tests/execution/test_cancel_all_orders_extension.py`)
- Test delta: 5,080 → 5,088 (= +8 new, no pre-existing test loss)
- Command used:
  - Baseline: `python -m pytest --ignore=tests/test_main.py -n auto -q` → `5080 passed in 61.81s`
  - Post-implementation: `python -m pytest --ignore=tests/test_main.py -n auto -q` → `5088 passed in 63.70s`
  - Scoped: `python -m pytest tests/execution/ -n auto -q` → `422 passed in 7.18s`
  - test_main.py: `python -m pytest tests/test_main.py -q` → `39 passed, 5 skipped`

### Unfinished Work
- **Invariant 21 (`test_no_oca_assertion_uses_simulated_broker` grep-guard) — DEFERRED to Session 1a.** The assertion exists to prove no OCA-related test relies on SimulatedBroker (which intentionally does not simulate OCA fill semantics). Session 0 introduces no OCA fields; Session 1a is where `Order.oca_group_id` lands and where the assertion has a binding. The prompt's note ("verify the test ... is added as part of Session 0 (or note it as deferred to Session 1a if more natural — but Session 0's close-out should explicitly call this out)") explicitly authorizes this deferral. Surfaced here per that instruction.

### Notes for Reviewer
- **AlpacaBroker latent bug preserved verbatim.** `self._check_connected()` is called inside `_cancel_all_orders_legacy` (line 799) but `_check_connected` is undefined on `AlpacaBroker` (only `SimulatedBroker` defines one). This is pre-Session-0 behavior. The prompt's "DO NOT touch the legacy function's body" took precedence; AlpacaBroker is queued for retirement in Sprint 31.94 (DEF-178/183) so this does not warrant fixing in this session. Surfaced as a `deferred_observations` entry in the structured appendix.
- **`asyncio.get_event_loop()` deprecation.** The IBKR polling loop uses `asyncio.get_event_loop().time()` for the deadline computation. In Python 3.12+ this is deprecated when there is no running loop, but inside an awaited coroutine `get_event_loop()` returns the running loop and `loop.time()` is the canonical monotonic source. This matches the pattern used elsewhere in the codebase. The 4th test (`test_cancel_all_orders_await_propagation_timeout_raises`) patches the function to inject deterministic wall-clock without real `sleep`, which keeps the test fast (<1s) and runs Python-version-agnostic.
- **Invariant 14 (Monotonic-safety property — "After Session 0" all 8 columns NO).** Confirmed: Session 0 adds a defensive API but does not wire it into any caller. `order_manager.py` is not modified. The new method is unreachable from the live SELL paths until Session 1c.
- **Invariant 21 deferred to Session 1a (see Unfinished Work).**
- **Bonus tests vs. prompt-enumerated 6.** I delivered 8 (the 6 enumerated + 2 SimulatedBroker regressions). All 8 are additive; the 6 from the prompt are individually present and named exactly as specified.

### CI Verification
- CI run URL: TBD — will be filled in once the close-out commit is pushed and CI completes on the final commit (per RULE-050).
- CI status: TBD (pre-push)

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "31.91",
  "session": "0",
  "verdict": "COMPLETE",
  "tests": {
    "before": 5080,
    "after": 5088,
    "new": 8,
    "all_pass": true
  },
  "files_created": [
    "tests/execution/test_cancel_all_orders_extension.py",
    "docs/sprints/sprint-31.91-reconciliation-drift/session-0-closeout.md"
  ],
  "files_modified": [
    "argus/execution/broker.py",
    "argus/execution/ibkr_broker.py",
    "argus/execution/simulated_broker.py",
    "argus/execution/alpaca_broker.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "Added 2 SimulatedBroker regression tests beyond the 6 prompt-enumerated tests (symbol-filter + no-args clears-everything).",
      "justification": "DEC-364 preservation on SimulatedBroker is a distinct code path from IBKR's reqGlobalCancel; the prompt's no-args preservation acceptance criterion benefits from explicit binding on the simulated path. Net additive."
    }
  ],
  "scope_gaps": [
    {
      "description": "Invariant 21 (`test_no_oca_assertion_uses_simulated_broker` grep-guard) deferred to Session 1a.",
      "category": "SMALL_GAP",
      "severity": "LOW",
      "blocks_sessions": [],
      "suggested_action": "Add the grep-guard alongside the `Order.oca_group_id` field landing in Session 1a, where the assertion has a meaningful binding. The prompt's regression checklist note explicitly authorizes deferral to Session 1a."
    }
  ],
  "prior_session_bugs": [
    {
      "description": "Latent AttributeError in `AlpacaBroker._cancel_all_orders_legacy`: calls `self._check_connected()` which is not defined on `AlpacaBroker` (only on `SimulatedBroker`). Pre-Session-0 behavior preserved verbatim per prompt instruction 'DO NOT touch the legacy function's body.'",
      "affected_session": "pre-existing (not from any prior 31.91 session)",
      "affected_files": ["argus/execution/alpaca_broker.py"],
      "severity": "LOW",
      "blocks_sessions": []
    }
  ],
  "deferred_observations": [
    "AlpacaBroker `_check_connected()` AttributeError latent bug — preserved verbatim per prompt; AlpacaBroker queued for retirement in Sprint 31.94 (DEF-178/183).",
    "Invariant 21 SimulatedBroker OCA-assertion tautology guard deferred to Session 1a per prompt-authorized natural fit.",
    "`asyncio.get_event_loop().time()` usage in IBKR polling loop — matches existing codebase patterns; tests patch to inject deterministic time, so Python-version-independent."
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Session 0 delivers the broker-side API contract only; no caller wiring. Five-file diff: broker.py (ABC + exception), ibkr_broker.py (live impl), simulated_broker.py (in-memory impl), alpaca_broker.py (DeprecationWarning stub + legacy rename), and the new test file. DEC-364 no-args contract preserved verbatim on all three implementations; verified by both targeted tests and the full 5,080-test pytest baseline holding. The IBKR polling loop sources its filter set fresh from `self._ib.openTrades()` each iteration (not from a cached snapshot) so consistency-after-cancel is observed correctly. The 2s timeout is hardcoded in the IBKR impl per prompt directive — config field deferred until at least Session 1c integration provides justification."
}
```
