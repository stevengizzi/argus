# Sprint 31.91, Session 0: `Broker.cancel_all_orders(symbol, await_propagation)` API Extension

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt. RULE-038 (grep-verify discipline) and RULE-050 (CI green) are particularly relevant.

2. Read these files to load context:
   - `argus/execution/broker.py` (specifically the `cancel_all_orders` ABC method around line 143 — verify line number, may have drifted)
   - `argus/execution/ibkr_broker.py` (specifically the `cancel_all_orders` impl around line 1086 — verify)
   - `argus/execution/alpaca_broker.py` (entire file — needed to understand DeprecationWarning placement and existing impl shape)
   - `argus/execution/simulated_broker.py` (specifically the `cancel_all_orders` impl around line 629 — verify)
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` (D1 acceptance criteria)
   - `docs/sprints/sprint-31.91-reconciliation-drift/spec-by-contradiction.md` (out-of-scope items, especially #5 AlpacaBroker exception)

3. Run the test baseline (DEC-328 — Session 1 of sprint, full suite):

   ```
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```

   Expected: 5,080 tests passing. If the baseline differs, halt and verify with operator before proceeding.

   Then verify:

   ```
   python -m pytest tests/test_main.py -q
   ```

   Expected: 39 pass + 5 skip.

4. Verify you are on the correct branch: **`main`** (this sprint works directly on `main` per the design summary; no feature branch).

5. Verify `git status` is clean before starting.

## Objective

Extend the `Broker` ABC's `cancel_all_orders()` signature to accept an optional `symbol` filter and a keyword-only `await_propagation` flag. Implement on `IBKRBroker`, `SimulatedBroker`, and add a `DeprecationWarning`-only impl on `AlpacaBroker` (queued for retirement in Sprint 31.94 per L1 disposition). This API is foundational — Session 1c uses `await_propagation=True` to make broker-only SELL paths safe by clearing stale OCA siblings before placing new SELLs.

## Requirements

1. **Create `CancelPropagationTimeout` exception** in `argus/execution/broker.py`:

   ```python
   class CancelPropagationTimeout(Exception):
       """Raised when cancel_all_orders(await_propagation=True) does not
       observe broker-side empty open-orders state within the timeout
       window. Callers should abort any planned follow-up SELL placement
       and emit a `cancel_propagation_timeout` SystemAlertEvent."""
   ```

2. **Update `Broker` ABC signature** in `argus/execution/broker.py` (around line 143):

   ```python
   @abstractmethod
   async def cancel_all_orders(
       self,
       symbol: str | None = None,
       *,
       await_propagation: bool = False,
   ) -> int:
       """Cancel working orders.

       Args:
           symbol: If provided, cancel only orders for this symbol.
               If None, cancel all working orders (DEC-364 contract).
           await_propagation: If True, after issuing cancellations,
               poll broker open-orders for the filtered scope until
               empty. Default 2s timeout. On timeout, raise
               CancelPropagationTimeout.

       Returns:
           Count of orders for which a cancellation was issued.
       """
   ```

   Preserve DEC-364 contract: when `symbol=None` and `await_propagation=False`, behavior must match the pre-Session-0 contract exactly.

3. **Implement on `IBKRBroker`** in `argus/execution/ibkr_broker.py` (around line 1086):
   - Filter the `ib_async` open-orders list by `contract.symbol == symbol` when symbol is provided.
   - When `await_propagation=True`, after issuing cancellations, poll `self._ib.openOrders()` (or the appropriate `ib_async` accessor — verify against the existing impl's pattern) every 100ms, filtered to the same `symbol` scope. Return successfully when the filtered list is empty. Raise `CancelPropagationTimeout` after 2s.
   - The 2s timeout is a constant in this method; do NOT add a config field for it in this session.

4. **Implement on `SimulatedBroker`** in `argus/execution/simulated_broker.py` (around line 629):
   - Filter the in-memory order tracking dict by `symbol` when provided.
   - `await_propagation=True` is essentially synchronous in `SimulatedBroker` (the cancel happens in-memory immediately), so the polling loop returns immediately after cancellation. No `CancelPropagationTimeout` path exercised.

5. **Implement on `AlpacaBroker`** in `argus/execution/alpaca_broker.py`:
   - The method must exist for ABC compliance.
   - Body: emit a `DeprecationWarning` and either delegate to the existing implementation OR raise `NotImplementedError` if extending the existing impl is non-trivial. Operator preference per L1: minimal stub that satisfies the ABC; DO NOT write throwaway functional code.
   - Suggested body:

     ```python
     async def cancel_all_orders(
         self,
         symbol: str | None = None,
         *,
         await_propagation: bool = False,
     ) -> int:
         import warnings
         warnings.warn(
             "AlpacaBroker.cancel_all_orders is queued for retirement "
             "in Sprint 31.94 (DEF-178/183). Symbol filtering and "
             "await_propagation are not implemented for this broker.",
             DeprecationWarning,
             stacklevel=2,
         )
         # Delegate to existing no-arg impl for backward-compat:
         return await self._cancel_all_orders_legacy()  # or whatever the existing impl was renamed to
     ```

   - If the existing AlpacaBroker `cancel_all_orders` impl was a single function, rename it to `_cancel_all_orders_legacy` and call it from the new ABC-compliant method. Do NOT touch the legacy function's body.

6. **Update existing call sites** that pass keyword arguments — there should be NONE since `await_propagation` is new. Existing call sites that pass `symbol=None` (or no args) should continue to work via the default.

## Constraints

- Do NOT modify:
  - `argus/execution/order_manager.py` — Session 1c will modify this to use the new API. Session 0 only delivers the API.
  - `argus/main.py` — startup invariant region. No changes here in Session 0.
  - `argus/models/trading.py` — `Position` class. No changes anywhere in this sprint.
  - `argus/data/alpaca_data_service.py` — Alpaca emitter TODO at `:593` is out of scope (anti-regression test in Session 5b).
  - DEC-364's existing semantics: `cancel_all_orders()` (no args) must still cancel everything.
  - The `workflow/` submodule (RULE-018).

- Do NOT change:
  - The 2s timeout constant location: leave it inline in the IBKR impl. Do NOT add a config field for `cancel_propagation_timeout_seconds`.
  - Any existing tests' call patterns (existing tests call `cancel_all_orders()` with no args; that must still work).
  - `IBKRBroker.place_bracket_order` rollback logic at `argus/execution/ibkr_broker.py:783-805` (DEC-117 atomic-bracket invariant).

- Do NOT cross-reference other session prompts. This prompt is standalone.

- Do NOT pre-emptively wire the new API into any caller. Session 1c is the integrator.

## Test Targets

After implementation:

- Existing tests: all 5,080 must still pass.
- New tests (~6 new pytest, all in a new file `tests/execution/test_cancel_all_orders_extension.py` or appended to existing `tests/execution/test_broker_*.py` if a natural home exists — verify during pre-flight):

  1. `test_cancel_all_orders_no_args_preserves_dec364`
     - Assert calling `cancel_all_orders()` with no args produces same behavior as pre-Session-0: cancellation issued for ALL working orders.
  2. `test_cancel_all_orders_symbol_filter`
     - Set up IBKRBroker mock with working orders for AAPL and TSLA. Call `cancel_all_orders(symbol="AAPL")`. Assert TSLA orders untouched.
  3. `test_cancel_all_orders_await_propagation_polls_until_empty`
     - Mock IBKR `openOrders()` to return [order] on first call, [] on second. Call `cancel_all_orders(symbol="AAPL", await_propagation=True)`. Assert returns successfully without raising. Assert poll happened ≥1 time.
  4. `test_cancel_all_orders_await_propagation_timeout_raises`
     - Mock IBKR `openOrders()` to always return non-empty. Call `cancel_all_orders(symbol="AAPL", await_propagation=True)`. Assert `CancelPropagationTimeout` raised within 2s + small buffer.
  5. `test_alpaca_broker_cancel_all_orders_raises_deprecation_warning`
     - Use `pytest.warns(DeprecationWarning)`. Assert legacy delegation still returns the old return value shape.
  6. `test_ibkr_broker_cancel_all_orders_symbol_filter_uses_open_orders`
     - Verify the IBKR impl filters via the `ib_async` open-orders accessor (not via cached state). The actual matching attribute is `Trade.contract.symbol`; verify the filter expression uses this.

- Test command: `python -m pytest tests/execution/ -n auto -q` (scoped — full suite runs at close-out).

## Config Validation (N/A this session)

Session 0 does not add config fields. The `bracket_oca_type` config arrives in Session 1a.

## Marker Validation (N/A this session)

Session 0 does not add pytest markers.

## Definition of Done

- [ ] Signature accepts `symbol: str | None = None, *, await_propagation: bool = False`.
- [ ] All 3 broker implementations updated: `IBKRBroker`, `SimulatedBroker`, `AlpacaBroker`.
- [ ] `AlpacaBroker.cancel_all_orders` raises `DeprecationWarning` (verified by test).
- [ ] DEC-364 contract preserved (no-args call cancels everything).
- [ ] `CancelPropagationTimeout` exception class exists in `argus/execution/broker.py`.
- [ ] All 6 new tests pass.
- [ ] Existing 5,080 pytest baseline holds; new tests are additive.
- [ ] `tests/test_main.py` baseline (39 pass + 5 skip) unchanged.
- [ ] CI green on the final commit.
- [ ] Tier 2 review CLEAR via @reviewer subagent.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| Existing pre-Session-0 callers of `cancel_all_orders()` (no args) still work | `grep -rn 'cancel_all_orders(' argus/ tests/` — every call site that passes no args must still execute identically |
| `git diff HEAD~1 -- argus/execution/order_manager.py` shows zero edits | `git diff HEAD~1 -- argus/execution/order_manager.py | wc -l` must be 0 |
| `git diff HEAD~1 -- argus/main.py` shows zero edits | `git diff HEAD~1 -- argus/main.py | wc -l` must be 0 |
| `git diff HEAD~1 -- argus/models/trading.py` shows zero edits | Same |
| `git diff HEAD~1 -- argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix) shows zero edits | Critical — invariant 1 |
| AlpacaBroker emits `DeprecationWarning` on call | Run `tests/execution/test_cancel_all_orders_extension.py::test_alpaca_broker_cancel_all_orders_raises_deprecation_warning` |
| Pre-existing flake count unchanged | CI run output: DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 fail at same or lower frequency |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ` ```json:structured-closeout `. See the close-out skill for the full schema and requirements.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.91-reconciliation-drift/session-0-closeout.md
```

Do NOT just print the report in the terminal. Create the file, write the full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.91-reconciliation-drift/session-0-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/execution/ -n auto -q` (scoped — DEC-328; this is a non-final session)
5. Files that should NOT have been modified:
   - `argus/execution/order_manager.py`
   - `argus/main.py`
   - `argus/models/trading.py`
   - `argus/data/alpaca_data_service.py`
   - `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`
   - `workflow/` submodule
   - Any file outside `argus/execution/{broker,ibkr_broker,simulated_broker,alpaca_broker}.py` and `tests/execution/test_cancel_all_orders_extension.py` (or wherever the new tests live)

The @reviewer will produce its review report (including a structured JSON verdict fenced with ` ```json:structured-verdict `) and write it to:

```
docs/sprints/sprint-31.91-reconciliation-drift/session-0-review.md
```

The @reviewer must use the **backend safety reviewer** template (`templates/review-prompt.md` from the workflow metarepo). This is a backend session.

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same session:

1. **Append a "Post-Review Fixes" section to the close-out report file** at `docs/sprints/sprint-31.91-reconciliation-drift/session-0-closeout.md`:

   ```markdown
   ### Post-Review Fixes
   The following findings from the Tier 2 review were addressed in this session:
   | Finding | Fix | Commit |
   |---------|-----|--------|
   | [description from review] | [what you changed] | [short hash] |
   ```

   Commit the updated close-out file.

2. **Append a "Resolved" annotation to the review report file** at `docs/sprints/sprint-31.91-reconciliation-drift/session-0-review.md`:

   ```markdown
   ### Post-Review Resolution
   The following findings were addressed by the implementation session
   after this review was produced:
   | Finding | Status |
   |---------|--------|
   | [description] | ✅ Fixed in [short hash] |
   ```

   Update the structured verdict JSON: change `"verdict": "CONCERNS"` to `"verdict": "CONCERNS_RESOLVED"` and add a `"post_review_fixes"` array. Commit the updated review file.

If the reviewer reports CLEAR or ESCALATE, skip this section. ESCALATE findings must NOT be fixed without human review.

## Session-Specific Review Focus (for @reviewer)

1. **DEC-364 contract preservation.** Verify that calling `cancel_all_orders()` with no args produces identical behavior to the pre-Session-0 contract. Inspect every call site in `argus/` and `tests/` via `grep -rn 'cancel_all_orders('` and confirm none break.

2. **`await_propagation` polling timeout edge cases:**
   - What happens if IBKR connection drops during the poll? (Should propagate the underlying error, not swallow.)
   - What happens if 0 orders existed in the first place? (Polling should return immediately on first check.)
   - What happens if cancellation succeeds in IBKR but `openOrders()` is briefly inconsistent? (Polling should retry until consistency.)

3. **AlpacaBroker `DeprecationWarning` style (per L1):**
   - Minimal stub, not throwaway functional code.
   - The `DeprecationWarning` message names Sprint 31.94 as the retirement target.
   - The legacy delegation preserves backward-compatibility for any existing call sites.

4. **`CancelPropagationTimeout` exception placement.** Should live in `argus/execution/broker.py` (the ABC module), not in `ibkr_broker.py` (impl-specific).

5. **No premature wiring.** Verify Session 1c is the integrator; Session 0 must not modify `order_manager.py` or any caller.

6. **Anti-regression on do-not-modify list.** Run `git diff HEAD~1 --stat` and verify only the expected files appear.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in
`docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`
under "Embedded: Sprint-Level Regression Checklist."

The 22 critical invariants must each be marked PASS / FAIL / N/A in
the review verdict report. Of particular relevance to Session 0:

- **Invariant 1 (DEF-199 A1 fix detects + refuses 100% of phantom shorts at EOD):** PASS — verify zero edits to `order_manager.py:1670-1750`.
- **Invariant 4 (DEC-117 atomic bracket invariant):** N/A — Session 0 doesn't touch bracket placement.
- **Invariant 5 (5,080 pytest baseline holds):** PASS — verify post-session count is 5,080 + new tests.
- **Invariant 7 (Vitest baseline holds at 866):** PASS — verify Vitest count unchanged (no frontend changes).
- **Invariant 9 (IMPROMPTU-04 startup invariant unchanged):** PASS — verify zero edits to `main.py` startup region.
- **Invariant 12 (Pre-existing flakes did not regress):** PASS — verify CI run.
- **Invariant 13 (New config fields):** N/A — Session 0 adds no config.
- **Invariant 14 (Monotonic-safety property):** Row "After Session 0" — all 8 columns NO. Verify no premature wiring.
- **Invariant 15 (No items on do-not-modify list touched):** PASS — verify the explicit list above.
- **Invariant 21 (SimulatedBroker OCA-assertion tautology guard):** This invariant LANDS at Session 0 close-out per the regression checklist note. Verify the `test_no_oca_assertion_uses_simulated_broker` test from invariant 21 is added as part of Session 0 (or note it as deferred to Session 1a if more natural — but Session 0's close-out should explicitly call this out).

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria are in
`docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`
under "Embedded: Sprint-Level Escalation Criteria."

If any A-class trigger fires during Session 0 implementation, the
implementer halts and posts to the work-journal conversation.

For Session 0 specifically:
- **A2** (any Tier 2 CONCERNS or ESCALATE) — operator + Tier 2 reviewer disposition.
- **B1** (pre-existing flake count increases) — file DEF entry; halt.
- **B3** (pytest baseline below 5,080) — halt; investigate.
- **B4** (CI red on final commit, not a documented flake) — halt per RULE-050.
- **B6** (do-not-modify file in `git diff`) — halt; revert.

---

*End Sprint 31.91 Session 0 implementation prompt.*
