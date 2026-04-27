# Sprint 31.91 — Session 0 Tier 2 Review

**Reviewer:** @reviewer subagent (Tier 2, backend safety template)
**Date:** 2026-04-27
**Session under review:** Sprint 31.91 — Session 0 (`Broker.cancel_all_orders(symbol, await_propagation)` API extension)
**Final commit:** `9b7246c` on `main`
**CI run:** [25011533575](https://github.com/stevengizzi/argus/actions/runs/25011533575) — **success** (pytest backend + vitest frontend, both green)
**Verdict:** **CLEAR**

---BEGIN-REVIEW---

## Summary

Session 0 delivers the broker-side API contract for the `cancel_all_orders(symbol, await_propagation)` extension cleanly. The implementation is surgical (4 broker files + 1 new test file), preserves DEC-364 byte-for-byte on no-args paths, adds a new `CancelPropagationTimeout` exception in the correct module (`broker.py`, not `ibkr_broker.py`), and intentionally avoids any caller wiring (Session 1c is the integrator). All 8 new tests pass; 5,080 → 5,088 pytest baseline holds; CI is green on the final commit; do-not-modify list shows zero edits.

The session's two judgment calls — preserving the latent `_check_connected` AttributeError in AlpacaBroker per the prompt's "DO NOT touch the legacy function's body" instruction, and deferring Invariant 21 to Session 1a per the prompt-authorized natural fit — are both correctly disclosed in the close-out. The +2 SimulatedBroker bonus tests are additive and well-justified.

No blocking issues. No CONCERNS. No ESCALATE.

## Methodology

1. Read review context (Sprint Spec, Spec by Contradiction, 22-invariant Regression Checklist, Escalation Criteria) at `docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`.
2. Read implementation prompt at `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-0-impl.md`.
3. Read close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-0-closeout.md`.
4. Verified `git diff HEAD~1 --name-only` enumerates only the expected paths.
5. Read each diff in full: `argus/execution/{broker,ibkr_broker,simulated_broker,alpaca_broker}.py` plus `tests/execution/test_cancel_all_orders_extension.py`.
6. Traced the 6 prompt-enumerated test names against the actual file; confirmed all 6 plus 2 additive bonus tests.
7. Re-ran scoped tests (`pytest tests/execution/ -n auto -q` → 422 passed) and the new test file in verbose mode (8/8 passed in 0.17s).
8. Ran focused regression `pytest tests/execution/order_manager/test_safety.py -k cancel_all_orders -q` → 1 passed (pre-existing no-args caller still works).
9. Verified `git diff HEAD~1` against do-not-modify list (combined diff = 0 lines).
10. Confirmed `git submodule status workflow` unchanged (RULE-018).
11. Polled GitHub Actions until CI run 25011533575 completed; confirmed `success` on final commit `9b7246c` (RULE-050).
12. Traced edge-case behaviors per the session-specific review focus.

## Findings

### F1 — DEC-364 contract preservation (PASS)

**Verification:** No-args call path on each implementation is structurally preserved.

- `IBKRBroker`: when `symbol is None`, the impl falls through to the existing `reqGlobalCancel` path with the existing `await asyncio.sleep(min(5.0, max(1.0, count * 0.5)))` confirmation wait. The pre-Session-0 line `self._ib.reqGlobalCancel()` is byte-identical inside the new `if symbol is None:` branch; nothing pre-existing was reordered.
- `SimulatedBroker`: when `symbol is None`, an explicit early-return clears `_pending_brackets` and returns the count — semantically equivalent to the pre-Session-0 body.
- `AlpacaBroker`: pre-Session-0 body renamed to `_cancel_all_orders_legacy`; new ABC method delegates via `await self._cancel_all_orders_legacy()`. Body byte-identical via `git show HEAD~1:argus/execution/alpaca_broker.py | sed -n '758,810p'` comparison — confirmed verbatim rename.

Existing call sites grep-verified: `argus/main.py:2268`, `tests/execution/order_manager/test_safety.py:367/393/995`, `tests/execution/order_manager/test_reconciliation.py:94`, `tests/execution/order_manager/test_reconciliation_redesign.py:91`. All call no-args; default `symbol=None, await_propagation=False` preserves DEC-364 exactly.

### F2 — `await_propagation` polling edge cases (PASS)

Traced each session-specific edge case the prompt called out:

1. **0 orders existed in the first place.** When the initial filter yields no orders, `count == 0` and the cancellation block is skipped. The `if await_propagation:` block is then reached; it calls `self._ib.openTrades()` again, applies the same symbol filter, observes `remaining = []`, and `break`s on the first iteration. ✅ returns immediately (no spurious 100ms sleep).

2. **IBKR connection drops during the poll.** `self._ib.openTrades()` is the source of truth and is re-queried each iteration; if it raises (e.g., `ConnectionError`), the exception propagates naturally — the impl wraps no `try/except` around the poll. ✅ propagated, not swallowed.

3. **Cancellation succeeds but `openOrders()` briefly inconsistent.** The poll loop re-queries `self._ib.openTrades()` every 100ms (sourced fresh, not from a cached snapshot), so once IBKR's open-orders cache catches up, the next iteration observes empty and breaks. ✅ consistency-after-cancel observed correctly.

4. **Connection check at start.** `if not self.is_connected: return 0` short-circuits before the poll, so no stale-cache poll-loop-against-disconnected-broker hazard. The 0-return is the conservative safe outcome.

5. **`symbol=None, await_propagation=True` (legitimate combination).** The polling is gated only by `if await_propagation:` (not by `if symbol is not None:`), so a global cancel with propagation-await works correctly. The per-iteration filter `if symbol is not None: remaining = [...]` is correctly skipped.

### F3 — `CancelPropagationTimeout` exception placement (PASS)

Defined at `argus/execution/broker.py:21-25`, in the ABC module, NOT in `ibkr_broker.py`. Imported by `ibkr_broker.py:32` from `argus.execution.broker`. ✅ correct placement per session-specific review focus item #4.

### F4 — AlpacaBroker DeprecationWarning style (PASS)

- Minimal stub: 17-line wrapper that calls `warnings.warn(..., DeprecationWarning, stacklevel=2)` then `await self._cancel_all_orders_legacy()`. No throwaway functional code (per L1).
- DeprecationWarning message names "Sprint 31.94 (DEF-178/183)" as the retirement target.
- Legacy delegation preserves backward-compatibility (renamed function body byte-identical, callable via the new ABC-compliant signature when no special params are passed).
- `stacklevel=2` correctly points the warning at the caller, not at the wrapper.
- Test `test_alpaca_broker_cancel_all_orders_raises_deprecation_warning` asserts both the warning category AND the "Sprint 31.94" string match.

### F5 — Latent `_check_connected` AttributeError preserved verbatim (PASS — properly disclosed)

The pre-Session-0 AlpacaBroker body called `self._check_connected()` at what is now line 799, but `_check_connected` is defined only on `SimulatedBroker` (12 sites, including `simulated_broker.py:113` definition). On `AlpacaBroker`, this would raise `AttributeError` on first invocation.

The close-out's "Notes for Reviewer" and `prior_session_bugs` entry in the structured JSON appendix both disclose this clearly. The prompt's instruction "DO NOT touch the legacy function's body" took precedence — RULE-001 (execute exactly what the prompt specifies) supports this interpretation. AlpacaBroker is queued for retirement in Sprint 31.94 (DEF-178/183), so the bug has a near-term horizon for either deletion or a separate fix.

Verified by `git show HEAD~1:argus/execution/alpaca_broker.py | sed -n '758,810p'` that the legacy body is byte-identical to the pre-Session-0 version. ✅ pure rename.

### F6 — No premature wiring (PASS)

`grep -rn cancel_all_orders argus/execution/order_manager.py` returns ZERO matches. The new API is unreachable from any production caller; Session 1c is the integrator. ✅ Invariant 14's "After Session 0" row (all 8 columns NO) is correctly preserved.

### F7 — Anti-regression on do-not-modify list (PASS)

`git diff HEAD~1 -- argus/execution/order_manager.py argus/main.py argus/models/trading.py argus/data/alpaca_data_service.py | wc -l` = **0 lines**. Combined diff is empty. ✅ all four files untouched.

`git diff HEAD~1 --name-only` shows only:
- `argus/execution/alpaca_broker.py`
- `argus/execution/broker.py`
- `argus/execution/ibkr_broker.py`
- `argus/execution/simulated_broker.py`
- `docs/sprints/sprint-31.91-reconciliation-drift/session-0-closeout.md`
- `tests/execution/test_cancel_all_orders_extension.py`

All 6 paths are explicitly in the permitted set per the impl prompt's `Files that should NOT have been modified` list (which excluded the four broker files, the new test file, and the close-out doc).

`git submodule status workflow` shows `0df05428b824774ff7f5e4d53d468e43dde55c75` — unchanged from before the session (RULE-018 satisfied).

### F8 — Test coverage matches prompt (PASS)

The prompt enumerated 6 tests; the file has 8 (the 6 + 2 additive SimulatedBroker bonuses):

| Prompt-enumerated | File location | Status |
|---|---|---|
| `test_cancel_all_orders_no_args_preserves_dec364` | `:60` | ✅ PASS |
| `test_cancel_all_orders_symbol_filter` | `:86` | ✅ PASS |
| `test_cancel_all_orders_await_propagation_polls_until_empty` | `:109` | ✅ PASS |
| `test_cancel_all_orders_await_propagation_timeout_raises` | `:139` | ✅ PASS |
| `test_alpaca_broker_cancel_all_orders_raises_deprecation_warning` | `:172` | ✅ PASS |
| `test_ibkr_broker_cancel_all_orders_symbol_filter_uses_open_orders` | `:193` | ✅ PASS |
| **Additive bonus**: `test_simulated_broker_cancel_all_orders_symbol_filter` | `:215` | ✅ PASS |
| **Additive bonus**: `test_simulated_broker_cancel_all_orders_no_args_clears_everything` | `:265` | ✅ PASS |

Bonus tests are well-justified — the `SimulatedBroker` symbol-filter path is structurally distinct from `IBKRBroker`'s `reqGlobalCancel` codepath, and exercising both is consistent with the implicit acceptance criterion that DEC-364 is preserved on every implementation. Net additive (no scope expansion).

### F9 — Test runtime (PASS)

8 new tests run in 0.17s. Full execution test suite (422 tests) runs in 5.83s under `-n auto`. No test exceeds 60s (B7 not triggered). Test 4 (`timeout_raises`) uses a `MagicMock` to inject deterministic event-loop time (`fake_times` iterator) so it never hits real wall-clock — confirmed in the diff at `test_cancel_all_orders_extension.py:151-163`.

### F10 — CI green on final commit (PASS — RULE-050)

CI run [25011533575](https://github.com/stevengizzi/argus/actions/runs/25011533575) on commit `9b7246c`:
- `pytest (backend)` — `success` (3m 53s)
- `vitest (frontend)` — `success` (1m 23s)

Verified post-completion via `gh run view 25011533575 --json status,conclusion,jobs`. Both jobs green. RULE-050 satisfied.

### F11 — Invariant 21 deferral (PASS — N/A)

`grep -rn test_no_oca_assertion_uses_simulated_broker tests/` returns zero matches — the guard is correctly NOT yet in the test suite. The prompt's regression-checklist note explicitly authorized deferral to Session 1a ("verify the test ... is added as part of Session 0 (or note it as deferred to Session 1a if more natural — but Session 0's close-out should explicitly call this out)"). Session 1a is when `Order.oca_group_id` lands and the assertion has a meaningful binding. The close-out's `Unfinished Work` and structured JSON `scope_gaps[0]` both surface this clearly.

This is the prompt-authorized natural fit. Verdict: PASS as N/A for Session 0; the guard MUST land in Session 1a per the spec. Deferral is well-disclosed.

### F12 — `asyncio.get_event_loop()` deprecation note (acknowledged, not blocking)

The IBKR poll loop uses `asyncio.get_event_loop().time()` for the deadline. In Python 3.12+ this is deprecated when called outside a running loop, but inside an awaited coroutine `get_event_loop()` returns the running loop and `loop.time()` is the canonical monotonic source. Project target is Python 3.11+ (per `pyproject.toml`); current CI runs on Python 3.11.8. The pattern matches existing code elsewhere in the codebase (close-out's "Notes for Reviewer" disclosed this). The 4th test patches `asyncio.get_event_loop` to inject a deterministic time source so the test is fast and Python-version-agnostic.

Forward-looking suggestion (NOT a blocker): a future cleanup could swap to `asyncio.get_running_loop().time()` to avoid the deprecation when ARGUS bumps the Python floor. This is **not** an issue for Session 0 — disclosure is complete and behavior is correct under the project's current Python 3.11 floor.

## Sprint-Level Regression Checklist (22 invariants)

| # | Invariant | Status | Notes |
|---|-----------|--------|-------|
| 1 | DEF-199 A1 fix detects + refuses 100% phantom shorts at EOD | PASS | `git diff HEAD~1 -- argus/execution/order_manager.py | wc -l` = 0; subsumes line range 1670-1750. |
| 2 | DEF-199 A1 EOD Pass 1 retry side-check preserved | PASS | Same — order_manager.py untouched. |
| 3 | DEF-158 dup-SELL prevention works for ARGUS=N, IBKR=N normal case | PASS | Order Manager untouched; behavior preserved by construction. |
| 4 | DEC-117 atomic bracket invariant | N/A | Session 0 doesn't touch bracket placement. |
| 5 | 5,080 pytest baseline holds; new tests additive | PASS | 5,080 → 5,088 (+8 new). Confirmed via close-out's full-suite run + scoped re-run by reviewer. |
| 6 | `tests/test_main.py` baseline (39 pass + 5 skip) | PASS | Close-out cites `39 passed, 5 skipped in 5.56s`. |
| 7 | Vitest baseline at 866 | PASS | No frontend changes (verified via `git diff HEAD~1 --name-only` showing zero `argus/ui/` paths). CI vitest job green. |
| 8 | Risk Manager `share_count <= 0` rejection unchanged | PASS | `argus/core/risk_manager.py` not in diff. |
| 9 | IMPROMPTU-04 startup invariant unchanged | PASS | `argus/main.py` not in diff. |
| 10 | DEC-367 margin circuit breaker unchanged | PASS | `argus/core/risk_manager.py` not in diff; `argus/execution/order_manager.py` not in diff. |
| 11 | Sprint 29.5 EOD flatten circuit breaker unchanged | PASS | `argus/execution/order_manager.py` not in diff. |
| 12 | Pre-existing flakes did not regress | PASS | CI green on final commit; no new red flakes; close-out's full-suite run reports 5,088 passed with no transitions. |
| 13 | New config fields parse without warnings | N/A | Session 0 adds no config fields (per prompt; `bracket_oca_type` lands Session 1a). |
| 14 | Monotonic-safety property — "After Session 0" all 8 columns NO | PASS | API delivered but unwired; `grep -rn cancel_all_orders argus/execution/order_manager.py` returns zero matches. |
| 15 | No items on do-not-modify list touched | PASS | Combined diff of 4 do-not-modify files = 0 lines; workflow submodule SHA unchanged. |
| 16 | Bracket placement performance does not regress | N/A | Session 0 doesn't touch bracket placement (Session 4 wires the slippage check). |
| 17 | Mass-balance assertion at session debrief | N/A | Session 4 delivers; observational only here. |
| 18 | Frontend banner cross-page persistence | N/A | Session 5e delivers. |
| 19 | WebSocket fan-out reconnect resilience | N/A | Session 5c delivers. |
| 20 | Acknowledgment audit-log persistence | N/A | Session 5a.1 + 5a.2 deliver. |
| 21 | SimulatedBroker OCA-assertion tautology guard | PASS as N/A | Prompt-authorized deferral to Session 1a; close-out's `Unfinished Work` and `scope_gaps[0]` explicitly call this out. Will be verified at Session 1a. |
| 22 | Spike script freshness (HIGH #5) | N/A | Lands at Session 4. |

**Score:** 22/22 marked correctly. Of these: 11 PASS (or PASS as N/A in Inv. 21's deferral case), 11 N/A (sessions later in the sprint or unrelated subsystems). No FAIL marks.

## Sprint-Level Escalation Criteria

| # | Trigger | Status |
|---|---------|--------|
| A2 | Tier 2 verdict CONCERNS or ESCALATE | ❌ NOT TRIGGERED — verdict is CLEAR. |
| B1 | Pre-existing flake count increases | ❌ NOT TRIGGERED — CI green; no new flakes. |
| B3 | Pytest baseline below 5,080 | ❌ NOT TRIGGERED — 5,080 → 5,088. |
| B4 | CI red on final commit | ❌ NOT TRIGGERED — CI run 25011533575 = success. |
| B6 | Do-not-modify file in `git diff` | ❌ NOT TRIGGERED — combined diff of do-not-modify list = 0 lines. |

No A-class, B-class, or C-class halt conditions met.

## Recommendations to Next Session (Session 1a)

1. **Land Invariant 21** (`test_no_oca_assertion_uses_simulated_broker` grep-guard) when `Order.oca_group_id` lands. The Session 0 close-out and this review both explicitly mark this as Session 1a's responsibility per the prompt-authorized deferral.

2. **Defensive Error 201 handling on T1/T2 submission** is in scope per Sprint Spec D2. The Session 1a prompt should explicitly sequence the `ocaType=1` setting alongside the rollback path so the atomic-bracket invariant (Invariant 4) remains intact.

3. **Bracket OCA group ID derivation** uses `f"oca_{parent_ulid}"` per M1 disposition. Session 1a should add `oca_group_id` field to `ManagedPosition` and persist it at bracket-confirmation time — Session 1b uses this to thread standalone-SELL OCA membership.

## Verdict

**CLEAR.** Session 0 cleanly delivers the API extension, preserves DEC-364, isolates the new behavior to broker-implementation files, leaves the do-not-modify list untouched, hits 100% test pass rate (8/8 new + 5,080 pre-existing baseline + 39/5 test_main.py), and lands CI green on the final commit `9b7246c`. The two judgment calls (latent AlpacaBroker bug preserved verbatim per prompt; Invariant 21 deferred to Session 1a per prompt-authorized note) are correctly disclosed in the close-out's `Unfinished Work`, `Notes for Reviewer`, `prior_session_bugs[]`, and `scope_gaps[]` fields. The +2 SimulatedBroker bonus tests are additive and well-justified.

Proceed to **Session 1a** (Bracket OCA grouping + Error 201 defensive handling) per the sprint plan.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "31.91",
  "session": "0",
  "verdict": "CLEAR",
  "reviewer": "Tier 2 @reviewer subagent (backend safety template)",
  "review_date": "2026-04-27",
  "final_commit": "9b7246c",
  "ci": {
    "run_id": 25011533575,
    "status": "completed",
    "conclusion": "success",
    "url": "https://github.com/stevengizzi/argus/actions/runs/25011533575",
    "jobs": [
      {"name": "pytest (backend)", "conclusion": "success"},
      {"name": "vitest (frontend)", "conclusion": "success"}
    ]
  },
  "tests": {
    "before": 5080,
    "after": 5088,
    "new": 8,
    "all_pass": true,
    "test_main_py": "39 pass + 5 skip (unchanged)",
    "scoped_run_command": "python -m pytest tests/execution/ -n auto -q",
    "scoped_run_result": "422 passed in 5.83s"
  },
  "files_modified_actual": [
    "argus/execution/alpaca_broker.py",
    "argus/execution/broker.py",
    "argus/execution/ibkr_broker.py",
    "argus/execution/simulated_broker.py",
    "tests/execution/test_cancel_all_orders_extension.py",
    "docs/sprints/sprint-31.91-reconciliation-drift/session-0-closeout.md"
  ],
  "do_not_modify_list_violations": [],
  "regression_checklist": {
    "total_invariants": 22,
    "pass_count": 11,
    "fail_count": 0,
    "na_count": 11,
    "deferred_with_authorization": [
      {
        "invariant": 21,
        "reason": "SimulatedBroker OCA-assertion tautology guard deferred to Session 1a per prompt-authorized natural fit (Order.oca_group_id field lands in 1a, providing the binding surface for the assertion). Close-out's Unfinished Work and scope_gaps[0] explicitly disclose."
      }
    ]
  },
  "escalation_triggers_fired": [],
  "judgment_calls_reviewed": [
    {
      "description": "AlpacaBroker latent _check_connected AttributeError preserved verbatim",
      "verdict": "ACCEPTABLE",
      "rationale": "Prompt explicitly forbade touching the legacy function's body. AlpacaBroker queued for retirement in Sprint 31.94 (DEF-178/183). Disclosure complete in close-out's prior_session_bugs[]."
    },
    {
      "description": "+2 SimulatedBroker bonus tests beyond the 6 prompt-enumerated tests",
      "verdict": "ACCEPTABLE",
      "rationale": "DEC-364 preservation on SimulatedBroker is structurally distinct from IBKR's reqGlobalCancel codepath. Net additive; no scope expansion."
    },
    {
      "description": "Invariant 21 deferred to Session 1a",
      "verdict": "ACCEPTABLE",
      "rationale": "Prompt's regression-checklist note explicitly authorized this deferral. Order.oca_group_id field landing in Session 1a provides the assertion's binding surface."
    }
  ],
  "session_specific_review_focus": {
    "dec364_contract_preservation": "PASS",
    "await_propagation_polling_edge_cases": "PASS",
    "alpaca_deprecation_warning_style": "PASS",
    "cancel_propagation_timeout_placement": "PASS",
    "no_premature_wiring": "PASS",
    "do_not_modify_anti_regression": "PASS"
  },
  "deferred_observations": [
    "asyncio.get_event_loop().time() usage in IBKR polling loop is acceptable on Python 3.11 floor; future cleanup could swap to asyncio.get_running_loop().time() when Python floor bumps to 3.12+. Not a blocker.",
    "AlpacaBroker._check_connected AttributeError will surface either in Sprint 31.94 deletion or via earlier targeted fix — out of scope here.",
    "Invariant 21 grep-guard MUST land in Session 1a alongside Order.oca_group_id field."
  ],
  "recommendations_to_next_session": [
    "Land Invariant 21 (test_no_oca_assertion_uses_simulated_broker) in Session 1a alongside Order.oca_group_id field arrival.",
    "Verify Sprint Spec D2's defensive Error 201 handling on T1/T2 submission preserves DEC-117 atomic-bracket rollback (Invariant 4).",
    "Use f\"oca_{parent_ulid}\" per M1 disposition for bracket OCA group ID derivation; persist on ManagedPosition.oca_group_id at bracket-confirmation time."
  ],
  "context_state": "GREEN"
}
```
