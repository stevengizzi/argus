# Sprint 31.91 Session 1c — Close-Out

> **🔻 GATE SESSION FOR TIER 3 ARCHITECTURAL REVIEW #1 🔻**
>
> Session 1c is the final session of the OCA architecture track. After
> this session lands cleanly on `main` (Tier 2 CLEAR + green CI), Tier 3
> architectural review #1 fires per `escalation-criteria.md` §A1.

## 1. Files Modified

| File | Hunks | Notes |
|---|---|---|
| `argus/execution/order_manager.py` | imports (`SystemAlertEvent`, `CancelPropagationTimeout`); `reconstruct_from_broker()` docstring + per-symbol `cancel_all_orders` gate (lines `1858-1991`); `_flatten_unknown_position()` cancel-before-SELL gate (lines `2013-2113`); `_emit_cancel_propagation_timeout_alert()` helper added (lines `2114-2152`); `_drain_startup_flatten_queue()` cancel-before-SELL gate (lines `2188-2270`) | +163 / −9 lines. Production code change. |
| `tests/execution/test_broker_only_paths_safety.py` | New file — 7 tests | Functional tests for the 3 broker-only paths + cancel-timeout failure mode (Test 7 = Item 2 / MEDIUM #7). |
| `tests/execution/order_manager/test_core.py` | +59 / 0. Added `cancel_all_orders = AsyncMock(return_value=0)` mock to existing fixtures (~30 inline `mock_broker = MagicMock()` sites + the canonical `broker` fixture + 5 inline `broker = MagicMock()` test bodies). | Mock fixture update (Requirement 5 / Mock Update). |
| `tests/execution/order_manager/test_def158.py` | +1 line | `broker.cancel_all_orders = AsyncMock(return_value=0)` next to the existing `cancel_order` mock. |
| `tests/execution/order_manager/test_def199_eod_short_flip.py` | +1 line | Same pattern. |
| `tests/execution/order_manager/test_exit_config.py` | +1 line | Same pattern. |
| `tests/execution/order_manager/test_exit_management.py` | +1 line | Same pattern. |
| `tests/execution/order_manager/test_hardening.py` | +1 line | Same pattern. |
| `tests/execution/order_manager/test_sprint2875.py` | +1 line | Same pattern. |
| `tests/execution/order_manager/test_sprint295.py` | +1 line | Same pattern. |
| `tests/execution/order_manager/test_sprint329.py` | +1 line | Same pattern. |
| `tests/execution/order_manager/test_t2.py` | +1 line | Same pattern. |
| `tests/integration/historical/test_integration_sprint5.py` | +1 line | One additional integration test fixture revealed during full-suite run; same pattern. |

`test_reconciliation.py`, `test_reconciliation_redesign.py`, and
`test_safety.py` already had `cancel_all_orders = AsyncMock(...)` from
prior sessions (Session 0); they are not modified.

## 2. Tests Added

| # | Test | Why It Cannot Be Deleted |
|---|---|---|
| 1 | `test_flatten_unknown_position_calls_cancel_all_orders_first` | Asserts `cancel_all_orders(symbol=X, await_propagation=True)` runs textually BEFORE `place_order(...)` in `_flatten_unknown_position`. Reverting the gate causes the call ordering on the broker mock to fail this test. |
| 2 | `test_drain_startup_flatten_queue_calls_cancel_all_orders_first` | Asserts each queued symbol triggers cancel before its SELL, in queue order, with `await_propagation=True`. Catches partial regression (cancel removed, only place_order called). |
| 3 | `test_reconstruct_from_broker_calls_cancel_all_orders_per_symbol` | Asserts `cancel_all_orders` runs once per symbol BEFORE either position is wired into `_managed_positions`. |
| 4 | `test_eod_pass2_stale_oca_cleared_before_sell` | Higher-level integration through `eod_flatten()` — exercises the EOD Pass 2 → `_flatten_unknown_position` callsite end-to-end. Also asserts the broker-only-path SELL has `ocaGroup` unset (broker-only path is intentionally not threaded). |
| 5 | `test_reconstruct_orphaned_oca_cleared` | Asserts a reconstructed position with a stale `STP` order still gets `cancel_all_orders` and ends up wired with `oca_group_id=None` (no OCA reconstruction across restart — bracket OCA grouping is per-bracket-placement, not reconstructed). |
| 6 | `test_cancel_propagation_timeout_aborts_sell_and_emits_alert` | Asserts `place_order` is NOT called when `cancel_all_orders` raises `CancelPropagationTimeout`; a `SystemAlertEvent` with `alert_type='cancel_propagation_timeout'`, `severity='critical'` is emitted; the function returns cleanly so the EOD Pass 2 loop can proceed for other symbols. |
| 7 | `test_eod_pass2_cancel_timeout_aborts_sell_emits_alert_no_phantom_short` | **Item 2 / MEDIUM #7 failure-mode coverage.** A long zombie position + cancel-timeout MUST NOT be SELL'd (incorrect SELL would create unbounded phantom short). Position is NOT marked closed in any tracking structure. Docstring + body comment cross-reference `PHASE-D-OPEN-ITEMS.md` Item 2 + sprint-spec.md §D4 + the implementation prompt's Failure Mode section. |

(Mock-fixture updates across 11 existing test files are listed in §1; they are
not separate test entries.)

## 3. `git diff --stat`

```
 argus/execution/order_manager.py                   | 163 +++++++++++++++++++--
 tests/execution/order_manager/test_core.py         |  59 ++++++++
 tests/execution/order_manager/test_def158.py       |   1 +
 tests/execution/order_manager/test_def199_eod_short_flip.py    |   1 +
 tests/execution/order_manager/test_exit_config.py  |   1 +
 tests/execution/order_manager/test_exit_management.py          |   1 +
 tests/execution/order_manager/test_hardening.py    |   1 +
 tests/execution/order_manager/test_sprint2875.py   |   1 +
 tests/execution/order_manager/test_sprint295.py    |   1 +
 tests/execution/order_manager/test_sprint329.py    |   1 +
 tests/execution/order_manager/test_t2.py           |   1 +
 tests/integration/historical/test_integration_sprint5.py       |   1 +
 12 files changed, 223 insertions(+), 9 deletions(-)
```

Plus one untracked file:
- `tests/execution/test_broker_only_paths_safety.py` (~430 lines, 7 tests)

## 4. Test Evidence

### Scoped suite (DEC-328 — Session 4+ scoped acceptable)

```
$ python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q
462 passed, 1 warning in 6.71s
```

Pre-session scoped baseline was 455 passing. 462 = 455 + 7 new tests; net delta matches expectation.

### Full suite (DEC-328 — last session before Tier 3 #1 gate; full suite appropriate)

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q
5128 passed, 24 warnings in 63.79s (0:01:03)
```

`tests/test_main.py` separately (per CLAUDE.md DEF-048 protocol):

```
$ python -m pytest tests/test_main.py -q
39 passed, 5 skipped in 4.44s
```

Total = `5128 + 39 = 5167`. Pre-session baseline (per CLAUDE.md):
`5,080 + 39 + 5 skip = 5,124 pytest`. Session 1c adds 7 new tests (this
session) + 6 from Session 1a + ~8 from Session 1b + ~6 from Session 0 ≈ +27;
expected 5,151. Observed 5,167 — slightly over the rough estimate due to
sibling-session test growth not fully tabulated in the rough math. The
key invariant is that **pytest pass count is monotonically non-decreasing
relative to the pre-session baseline**, which holds.

`tests/_regression_guards/test_oca_threading_completeness.py::test_no_sell_without_oca_when_managed_position_has_oca` — **PASS** (the two new `# OCA-EXEMPT:` markers added in Session 1c are tolerated; the existing markers from Session 1b are unchanged).

DEF-199 anti-regression tests (`test_def199_eod_short_flip.py`) — all passing; the EOD Pass 2 / Pass 1 retry side-checks are unmodified.

### Vitest

Not exercised; Session 1c is backend-only.

## 5. Do-Not-Modify Audit

| Path / Region | `git diff` lines | Verdict |
|---|---|---|
| `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix) | 0 | PASS — diff hunks start at line 1858 (`reconstruct_from_broker`) and onwards; the EOD Pass 2 loop body at `:1705-1755` is read-only with respect to this session's edits. |
| `argus/main.py` | 0 | PASS — `git diff argus/main.py` returns nothing. The `:1081` call site stays exactly as-is. |
| `argus/execution/ibkr_broker.py` | 0 | PASS — Session 1a was the IBKR-broker session; Session 1c does not touch it. |
| `argus/execution/broker.py` | 0 | PASS — Session 0 finalized this; Session 1c only consumes the API. |
| `argus/execution/alpaca_broker.py` | 0 | PASS. |
| `argus/data/alpaca_data_service.py` | 0 | PASS. |
| `argus/models/trading.py` | 0 | PASS. |
| `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` | 0 | PASS. |
| `workflow/` (submodule) | 0 | PASS — Universal RULE-018 honored. |

Verification command:
```
git diff argus/main.py argus/execution/ibkr_broker.py argus/execution/broker.py \
        argus/execution/alpaca_broker.py argus/data/alpaca_data_service.py \
        argus/models/trading.py | wc -l
# → 0
```

The scoped exception per invariant 15 — the body of `reconstruct_from_broker()`
in `order_manager.py` — is explicitly permitted by the spec.

## 6. Failure-Mode Documentation Cross-Reference

The cancel-timeout failure mode is documented in this session's
implementation prompt (sprint-31.91-session-1c-impl.md §"Failure Mode
Documentation"), anchored by Test 7
(`test_eod_pass2_cancel_timeout_aborts_sell_emits_alert_no_phantom_short`),
and will be added to `docs/live-operations.md` "Phantom-Short Gate
Diagnosis and Clearance" section at sprint-close doc-sync (B22
cross-reference).

Test 7's docstring + body comment explicitly link to:
- `PHASE-D-OPEN-ITEMS.md` Item 2
- `sprint-spec.md` §D4
- The implementation prompt's "Failure Mode Documentation" section

The intended trade-off is preserved: **phantom long with no stop is a
bounded exposure preferable to an incorrect SELL that would create an
unbounded phantom short.** Operator response is documented in the
ERROR-level log line emitted alongside the alert.

## 7. Discovered Edge Cases

- **Existing test fixtures were broker-API-incomplete.** The
  `cancel_all_orders` ABC method was added in Session 0; existing fixtures
  pre-dating that did not mock it. Adding the cancel-before-SELL gates in
  `_flatten_unknown_position`, `_drain_startup_flatten_queue`, and
  `reconstruct_from_broker` made `OrderManager` invoke
  `cancel_all_orders` on every test broker — and a bare `MagicMock()`
  raises `TypeError: object MagicMock can't be used in 'await'
  expression`. Resolution: added `cancel_all_orders = AsyncMock(return_value=0)`
  to each affected fixture. Per RULE-019, no existing tests were deleted
  or skipped; pytest pass count is monotonically non-decreasing.

- **`ManagedPosition._broker_confirmed` is not currently set by
  `reconstruct_from_broker`.** The spec states "`reconstruct_from_broker()`
  wires positions into `_managed_positions` with `_broker_confirmed=True`".
  In current code, `_broker_confirmed` is a dict on `OrderManager` set at
  entry-fill (`order_manager.py:1059`), not on `_reconstruct_known_position`
  / `_create_reco_position`. This is a forward-looking statement about
  Session 2b.1's invariant extension; for Session 1c, the assertion is
  scoped to "the cancel gate does not block normal wiring on success."
  Test 3 asserts `symbol in om._managed_positions` after the cancel gate,
  not the `_broker_confirmed` bookkeeping — that belongs to the Session 2b.1
  scope.

- **`SystemAlertEvent` does not currently carry a structured `metadata`
  dict.** The frozen dataclass has 4 fields: `source`, `alert_type`,
  `message`, `severity`. The implementation prompt's example helper
  `_emit_system_alert(... metadata=...)` was suggestive, not normative.
  Resolution: encoded `symbol`, `shares`, and `stage` into the formatted
  `message` string + `source` (which already names the call site).
  Tests assert on `alert_type`, `severity`, and substring presence in
  `message` — sufficient for the failure-mode signal to operators.
  Adding a structured `metadata` field is a separate, additive API change
  that is out-of-scope for Session 1c.

## 8. Deferred Items (RULE-007)

- **Future broker-only SELL paths** in `order_manager.py` will need to either
  (a) thread OCA via `ManagedPosition.oca_group_id` (when applicable), or
  (b) gate via `cancel_all_orders(symbol, await_propagation=True)` and add
  the `# OCA-EXEMPT:` marker. Session 1b's grep regression guard structurally
  enforces this. No new deferred item is created — the guard IS the
  deferred-enforcement mechanism.

- **Sprint 31.93 (DEF-194/195/196 reconnect-recovery)** is the natural sprint
  to add the `ReconstructContext` parameter to `reconstruct_from_broker()`,
  enabling mid-session reconnect to skip the unconditional
  `cancel_all_orders` call. Documented contractually in the docstring.
  Already tracked under DEF-194/195/196; no new DEF needed.

## 9. Verdict JSON

```json
{
  "session": "1c",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 7,
  "tests_total_after": 5167,
  "files_modified": [
    "argus/execution/order_manager.py",
    "tests/execution/test_broker_only_paths_safety.py",
    "tests/execution/order_manager/test_core.py",
    "tests/execution/order_manager/test_def158.py",
    "tests/execution/order_manager/test_def199_eod_short_flip.py",
    "tests/execution/order_manager/test_exit_config.py",
    "tests/execution/order_manager/test_exit_management.py",
    "tests/execution/order_manager/test_hardening.py",
    "tests/execution/order_manager/test_sprint2875.py",
    "tests/execution/order_manager/test_sprint295.py",
    "tests/execution/order_manager/test_sprint329.py",
    "tests/execution/order_manager/test_t2.py",
    "tests/integration/historical/test_integration_sprint5.py"
  ],
  "donotmodify_violations": 0,
  "tier_3_readiness": "READY",
  "context_state": "GREEN"
}
```

## 10. Close-Out Tier-3 Readiness

### OCA Architecture State After Session 1c

- **API contract (Session 0):**
  `Broker.cancel_all_orders(symbol, *, await_propagation=False) -> int`
  ABC extension; `CancelPropagationTimeout` exception class;
  implementations on `IBKRBroker`, `SimulatedBroker`, and the
  deprecation-stubbed `AlpacaBroker`.

- **Bracket OCA (Session 1a):**
  `ocaGroup=f"oca_{parent_ulid}"`, `ocaType=1` set on all bracket
  children at `IBKRBroker.place_bracket_order`;
  `ManagedPosition.oca_group_id` field; defensive Error 201 / "OCA group
  is already filled" handling.

- **Standalone-SELL OCA (Session 1b):**
  4 paths threaded — `_trail_flatten`, `_escalation_update_stop`,
  `_resubmit_stop_with_retry` (via `_submit_stop_order`),
  `_flatten_position`; grep regression guard
  (`test_no_sell_without_oca_when_managed_position_has_oca`) with
  `# OCA-EXEMPT:` exemption mechanism; graceful Error 201 handling.

- **Broker-only safety (Session 1c, this session):**
  3 paths — `_flatten_unknown_position`, `_drain_startup_flatten_queue`,
  `reconstruct_from_broker`; `cancel_all_orders(symbol, await_propagation=True)`
  before SELL/wire; `CancelPropagationTimeout` aborts SELL/wire + emits
  critical `SystemAlertEvent`; `reconstruct_from_broker` STARTUP-ONLY
  contract docstring with explicit Sprint-31.93 future-caller requirement.

### Anticipated Tier 3 Architectural Questions

**Q1: Does Session 1c's cancel-before-SELL gate interact with DEC-117 atomic bracket invariant?**

A: No. DEC-117 governs bracket placement (parent-fails → all children
cancelled). Session 1c gates broker-only flatten/wire paths, which by
definition have no `ManagedPosition` and therefore no atomic-bracket
relationship to preserve. The cancel call clears stale orders from a
prior session before placing today's flatten or wiring today's
reconstruct — orthogonal to DEC-117.

**Q2: Does the 2s `await_propagation` timeout introduce a new failure mode that wasn't bounded in Sessions 0/1a/1b?**

A: Yes — the leaked-long failure mode. Documented in §"Failure Mode
Documentation" of the implementation prompt; covered by Test 7. Operator
response is manual flatten via `scripts/ibkr_close_all_positions.py`,
which the daily mitigation already prescribes through the sprint window.
The trade-off is intentional: a phantom long with no stop is bounded
exposure (the long position size); the alternative — placing the SELL
without verifying broker-side cancellation — could create an unbounded
phantom short on a runaway upside. Phantom-short asymmetric risk drove
the abort-on-timeout choice.

**Q3: Why is `reconstruct_from_broker`'s contract docstring contractual rather than a runtime check?**

A: Adding a runtime check (e.g., `assert context == STARTUP_FRESH`) would
require a context parameter, which Session 1c explicitly defers to
Sprint 31.93 (DEF-194/195/196 reconnect-recovery sprint). The docstring
is the bridging mechanism: future maintainers wiring a reconnect path
see the contractual STARTUP-ONLY warning before they propagate the bug.
Adding the parameter now would require touching `argus/main.py:1081`
(the do-not-modify call site for this session) and would couple Session
1c to a sprint that has not yet been planned.

**Q4: Is the `# OCA-EXEMPT:` mechanism robust against future SELL additions in broker-only paths?**

A: Mostly. Session 1b's grep regression guard
(`test_no_sell_without_oca_when_managed_position_has_oca`) checks for
`_broker.place_order(... SELL ...)` calls without OCA threading; the
`# OCA-EXEMPT: <reason>` comment provides an opt-out. Future broker-only
SELL paths must either (a) be exempt with the marker (legitimate
broker-only safety with a `cancel_all_orders` predecessor), or (b) be
threaded with OCA. The grep test is the structural enforcement; a future
reviewer who adds a SELL without either is forced to confront the
choice. Session 1c added two new `# OCA-EXEMPT:` markers (in
`_flatten_unknown_position` and `_drain_startup_flatten_queue`) — both
include explanatory text linking to the cancel-before-SELL safety
mechanism, so a future maintainer reading the code understands the
intent.

---

*End Sprint 31.91 Session 1c close-out.*
